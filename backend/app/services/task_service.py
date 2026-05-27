import asyncio
import json
import traceback
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.task import Task
from app.models.uploaded_file import UploadedFile
from app.models.generated_file import GeneratedFile
from app.services.progress_service import add_progress_event, cleanup_task_queue
from app.services.file_parser_service import parse_file
from app.services.ai_service import get_ai_config, build_user_prompt, build_image_data_url, call_ai_api
from app.services.export_service import export_deliverable


SUPPORTED_DELIVERABLE_FORMATS = {"txt", "docx", "pdf", "xlsx"}


def _normalize_deliverables(structured_output: dict) -> list[dict]:
    raw_deliverables = structured_output.get("deliverables")
    if not isinstance(raw_deliverables, list):
        structured_output["deliverables"] = []
        return []

    deliverables = []
    for index, item in enumerate(raw_deliverables, 1):
        if not isinstance(item, dict):
            continue

        fmt = str(item.get("format", "")).lower().lstrip(".")
        if fmt not in SUPPORTED_DELIVERABLE_FORMATS:
            continue

        content = item.get("content")
        if content is None or content == "":
            continue

        item["format"] = fmt
        item["id"] = str(item.get("id") or f"deliverable_{index}")
        item["title"] = str(item.get("title") or f"產出檔案 {index}")
        item["filename"] = str(item.get("filename") or f"{item['id']}.{fmt}")
        item["purpose"] = str(item.get("purpose") or "AI 決定產生的檔案")
        deliverables.append(item)

    structured_output["deliverables"] = deliverables
    return deliverables


async def run_task(task_id: str):
    try:
        await add_progress_event(task_id, "start", "任務建立中")

        async with async_session() as db:
            result = await db.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return

            task.status = "processing"
            task.updated_at = datetime.now(timezone.utc)
            await db.commit()

        await add_progress_event(task_id, "upload", "檔案上傳完成")

        # Parse files
        await add_progress_event(task_id, "parse", "檔案解析中")
        course_materials = []
        assignment_files = []

        async with async_session() as db:
            result = await db.execute(
                select(UploadedFile).where(UploadedFile.task_id == task_id)
            )
            files = list(result.scalars().all())

        for f in files:
            parsed_text, parsed_table, status = await asyncio.to_thread(
                parse_file, f.stored_path, f.file_type
            )

            async with async_session() as db:
                result = await db.execute(
                    select(UploadedFile).where(UploadedFile.id == f.id)
                )
                file_obj = result.scalar_one()
                file_obj.parsed_text = parsed_text
                file_obj.parsed_table_json = parsed_table
                file_obj.parse_status = "success" if status == "success" else "failed"
                file_obj.error_message = None if status == "success" else status
                await db.commit()

            file_data = {
                "filename": f.original_filename,
                "text": parsed_text,
                "tables": parsed_table,
            }
            image_data_url = build_image_data_url(f.stored_path, f.file_type)
            if image_data_url:
                file_data["image_data_url"] = image_data_url

            if f.file_category == "course_material":
                course_materials.append(file_data)
            else:
                assignment_files.append(file_data)

            if status != "success":
                await add_progress_event(
                    task_id, "parse",
                    f"檔案「{f.original_filename}」解析失敗：{status}",
                    detail={"file_id": f.id, "error": status},
                )
            else:
                await add_progress_event(
                    task_id, "parse",
                    f"檔案「{f.original_filename}」解析完成",
                    detail={"file_id": f.id, "text_length": len(parsed_text) if parsed_text else 0},
                )

        # Get task data
        async with async_session() as db:
            result = await db.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one()
            assignment_text = task.assignment_text

        await add_progress_event(task_id, "analyze", "課程資料整理中")
        await add_progress_event(task_id, "analyze", "作業需求分析中")

        # Build prompt and call AI
        config = await get_ai_config()
        user_prompt = build_user_prompt(assignment_text, course_materials, assignment_files)

        input_summary_parts = []
        if course_materials:
            input_summary_parts.append(f"課程資料：{len(course_materials)} 份")
        if assignment_files:
            input_summary_parts.append(f"作業檔案：{len(assignment_files)} 份")
        input_summary_parts.append(f"作業敘述：{len(assignment_text)} 字")

        await add_progress_event(task_id, "generate", "產生回答架構中")
        await add_progress_event(task_id, "generate", "生成草稿中")

        structured_output = await call_ai_api(
            config["system_prompt"], user_prompt, config
        )

        await add_progress_event(task_id, "generate", "檢查引用與格式中")

        deliverables = _normalize_deliverables(structured_output)
        output_text = (
            structured_output.get("explanation")
            or structured_output.get("generated_draft")
            or (deliverables[0].get("content") if deliverables else "")
        )
        if not isinstance(output_text, str):
            output_text = json.dumps(output_text, ensure_ascii=False, indent=2)

        async with async_session() as db:
            result = await db.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one()
            task.input_summary = "；".join(input_summary_parts)
            task.output_text = output_text
            task.structured_output_json = structured_output
            task.updated_at = datetime.now(timezone.utc)
            await db.commit()

        # Export files
        await add_progress_event(task_id, "export", "依 AI 決定建立輸出檔案中")

        for deliverable in deliverables:
            fmt = deliverable["format"]
            file_id = str(uuid.uuid4())
            deliverable["file_id"] = file_id
            try:
                file_path = await asyncio.to_thread(export_deliverable, task_id, deliverable)
                deliverable["status"] = "success"

                async with async_session() as db:
                    gen_file = GeneratedFile(
                        id=file_id,
                        task_id=task_id,
                        format=fmt,
                        file_path=file_path,
                        status="success",
                    )
                    db.add(gen_file)
                    await db.commit()

                await add_progress_event(
                    task_id, "export",
                    f"{deliverable['title']}（{fmt.upper()}）建立完成",
                )
            except Exception as e:
                deliverable["status"] = "failed"
                deliverable["error_message"] = str(e)
                async with async_session() as db:
                    gen_file = GeneratedFile(
                        id=file_id,
                        task_id=task_id,
                        format=fmt,
                        file_path="",
                        status="failed",
                        error_message=str(e),
                    )
                    db.add(gen_file)
                    await db.commit()

                await add_progress_event(
                    task_id, "export",
                    f"{deliverable['title']}（{fmt.upper()}）建立失敗：{str(e)}",
                )

        # Mark complete
        async with async_session() as db:
            result = await db.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one()
            task.status = "completed"
            task.output_formats = [item["format"] for item in deliverables if item.get("status") == "success"]
            task.structured_output_json = structured_output
            task.updated_at = datetime.now(timezone.utc)
            await db.commit()

        await add_progress_event(task_id, "complete", "任務完成")

    except Exception as e:
        async with async_session() as db:
            result = await db.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if task:
                task.status = "failed"
                task.error_message = str(e)
                task.updated_at = datetime.now(timezone.utc)
                await db.commit()

        await add_progress_event(
            task_id, "error",
            f"任務失敗：{str(e)}",
        )
    finally:
        cleanup_task_queue(task_id)

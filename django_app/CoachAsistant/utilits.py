import json


def safe_get_answer_from_message(msg) -> str:
    """
    Универсальный извлекатель ответа:
    1) parsed (pydantic)
    2) tool_calls[0].function.arguments (как JSON с ключом answer)
    3) raw content (JSON или просто текст)
    Возвращает строку.
    """
    # 1) parsed
    parsed = getattr(msg, "parsed", None)
    if parsed is not None:
        # pydantic BaseModel -> поле answer
        try:
            return parsed.answer
        except Exception:
            pass

    # 2) tool calls (если объявлялись tools)
    tool_calls = getattr(msg, "tool_calls", None)
    if tool_calls:
        args = tool_calls[0].function.arguments
        try:
            obj = json.loads(args) if isinstance(args, str) else args
            if isinstance(obj, dict) and "answer" in obj:
                return str(obj["answer"])
        except Exception:
            # если arguments не JSON — упадём на шаг 3
            pass

    # 3) raw content
    raw = (getattr(msg, "content", None) or "").strip()
    if not raw:
        return ""  # пусто — вернём пустую строку
    # возможно, это json
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and "answer" in obj:
            return str(obj["answer"])
        # если это был валидный json, но без "answer" — вернём как строку
        return raw
    except json.JSONDecodeError:
        # не json — вернём как есть
        return raw

def safe_url(request, file_field):
    if file_field and hasattr(file_field, "url"):
        return request.build_absolute_uri(file_field.url)
    return None

def get_ended_files(request, exercise):
    audio_raw = [exercise.end_audio]
    pdf_raw = [exercise.end_pdf]
    audio_clear_list = [f for f in audio_raw if f]
    pdf_clear_list = [f for f in pdf_raw if f]
    return audio_clear_list, pdf_clear_list

def get_started_files(request, exercise):
    audio_raw = [
        exercise.start_audio,
        exercise.additional_audio
    ]
    pdf_raw = [
        exercise.start_pdf,
        exercise.additional_pdf
    ]
    audio_clear_list = [f for f in audio_raw if f]
    pdf_clear_list = [f for f in pdf_raw if f]
    return audio_clear_list, pdf_clear_list
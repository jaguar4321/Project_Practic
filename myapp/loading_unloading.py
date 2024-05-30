import mimetypes
from django.http import HttpResponse
import os
from .data_loader import handle_archive
import shutil
from .data_loader import load_data_from_excel, load_discipline_from_excel, load_visiting_from_csv

def handle_uploaded_folder(folder, process_function):
    try:
        uploads_dir = 'uploads'
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
        file_path = os.path.join('uploads', folder.name)
        with open(file_path, 'wb+') as destination:
            for chunk in folder.chunks():
                destination.write(chunk)
        _, file_extension = os.path.splitext(folder.name)
        if file_extension.lower() in ['.zip', '.7z']:
            result = handle_archive(file_path, process_function)
        else:
            result = process_function(file_path)
        result.append(clear_folder(uploads_dir))
        return result
    except Exception as e:
        error_message = "Error while handling uploaded folder: " + str(e)
        return error_message


def download_file(request, file_path):
    if file_path:
        # Проверяем, существует ли файл по указанному пути
        if os.path.exists(file_path):
            # Определяем MIME-тип файла
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'

            # Открываем файл для скачивания
            with open(file_path, 'rb') as file:
                response = HttpResponse(file.read(), content_type=mime_type)
                # Устанавливаем заголовок Content-Disposition для предложения сохранить файл
                response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(file_path)
            return response
        else:
            # Возвращаем сообщение об ошибке, если файл не найден
            response = HttpResponse("File not found.")
            response.status_code = 404  # Устанавливаем код состояния 404 (файл не найден)
            return response
    else:
        # Возвращаем сообщение об ошибке, если путь к файлу не указан
        response = HttpResponse("File path is not provided.")
        response.status_code = 400  # Устанавливаем код состояния 400 (некорректный запрос)
        return response


def clear_folder(folder_path):
    folder_path = os.path.abspath(folder_path)
    error_message = ""

    try:
        if os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            return f"Тека '{folder_path}' успішно очищена."
        else:
            error_message = f"Тека '{folder_path}' не існує."
    except Exception as e:
        error_message = f"Сталася помилка при очищенні теки '{folder_path}': {e}"

    return error_message
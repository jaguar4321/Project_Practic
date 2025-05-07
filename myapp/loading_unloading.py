import logging
import mimetypes
from django.http import HttpResponse
import os
from .data_loader import handle_archive
import shutil
from .data_loader import load_data_from_excel, load_discipline_from_excel, load_visiting_from_csv


def handle_uploaded_folder(folder, process_function):
    errors = {
        'file_errors': [],
        'discipline_errors': [],
        'student_errors': [],
        'visit_errors': [],
        'format_errors': [],
        'archive_errors': [],
        'cleanup_errors': []
    }
    try:
        uploads_dir = 'uploads'
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
        file_path = os.path.join(uploads_dir, folder.name)
        with open(file_path, 'wb+') as destination:
            for chunk in folder.chunks():
                destination.write(chunk)
        _, file_extension = os.path.splitext(folder.name)

        if file_extension.lower() in ['.zip', '.7z']:
            archive_result = handle_archive(file_path, process_function)
            if isinstance(archive_result, dict):
                for key, value in archive_result.items():
                    if isinstance(value, list):
                        errors[key].extend(value)
                    else:
                        errors[key].append(value)
            else:
                errors['file_errors'].append(f"Помилка під час обробки файлу")
        else:
            file_errors = process_function(file_path)

            if isinstance(file_errors, dict):
                for key, value in file_errors.items():
                    if key not in errors:
                        errors[key] = []
                    if isinstance(value, list):
                        errors[key].extend(value)
                    else:
                        errors[key].append(value)
            else:
                errors['file_errors'].append(f"Помилка під час обробки файлу")

        cleanup_result = clear_folder(uploads_dir)
        if cleanup_result:
            errors['cleanup_errors'].append(cleanup_result)

        return errors
    except Exception as e:
        errors['file_errors'].append(f"Помилка під час обробки файлу: {str(e)}")
        return errors


def download_file(request, file_path):
    if file_path:

        if os.path.exists(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'

            with open(file_path, 'rb') as file:
                response = HttpResponse(file.read(), content_type=mime_type)
                response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(file_path)
            return response
        else:
            response = HttpResponse("File not found.")
            response.status_code = 404
            return response
    else:
        response = HttpResponse("File path is not provided.")
        response.status_code = 400
        return response

def clear_folder(folder_path):
    try:
        shutil.rmtree(folder_path)
        return None
    except Exception as e:
        return f"Помилка під час очищення папки {folder_path}: {str(e)}"
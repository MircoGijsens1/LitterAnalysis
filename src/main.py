import flet as ft
import os
import json
import shutil
from flet import FilePickerUploadFile
from datetime import datetime, timedelta, timezone
import asyncio
from firebase_admin import credentials, initialize_app, delete_app, get_app, _apps
from firebase_admin import firestore, storage, firestore_async
from google.cloud.storage import Client, transfer_manager
from google.oauth2 import service_account
import pandas as pd
from collections import defaultdict
from pathlib import Path
from ultralytics import YOLO
import cv2
import types

app_data_path = os.getenv("FLET_APP_STORAGE_DATA")
settings_path = os.path.join(app_data_path, "settings.json")

db = None
#bucket = None
gcs_client = None
gcs_bucket = None
#print(storage.transfer_manage)
def is_generator(obj):
    return isinstance(obj, types.GeneratorType)
def reinitialize_firebase(credential_path, bucket_name):
    global db, gcs_client, gcs_bucket
    try: 
        if _apps:
            delete_app(get_app())
        
        full_cred_path = os.path.join(app_data_path, credential_path)
        cred = credentials.Certificate(full_cred_path)
        initialize_app(cred, {
            "storageBucket": bucket_name
        })
        db = firestore_async.client()
        #bucket = storage.bucket()
        gcs_credentials = service_account.Credentials.from_service_account_file(full_cred_path)
        gcs_client = Client(credentials=gcs_credentials)
        gcs_bucket = gcs_client.bucket(bucket_name)

        print("Firebase and GCS re-initialized successfully.")
        print("Firebase re-initialized successfully.")
    except Exception as e:
        print("Firebase:", e)


try:
    with open(settings_path, "r") as file:
        settings_data = json.load(file)
except Exception as e:
    print("Failed to read JSON:", e)

if os.path.exists(os.path.join(app_data_path,settings_data["FirebaseCredentials"]["path"])) and settings_data["FirebaseCredentials"]["StorageBucket"]:
    reinitialize_firebase(settings_data["FirebaseCredentials"]["path"], settings_data["FirebaseCredentials"]["StorageBucket"])
else:
    print("File not found.")


def main(page: ft.Page):
    sucess_message = ft.SnackBar(
        duration="3000",
        content=ft.Text("✅ Upload successful!", color=ft.Colors.GREEN),
        bgcolor=ft.Colors.ON_SURFACE_VARIANT
    )
    def show_success():
        page.open(sucess_message)
        page.update()
        
    error_text = ft.Text("Something went wrong", color=ft.Colors.RED)
    error_message = ft.SnackBar(
        duration="3000",
        content=error_text,
        bgcolor=ft.Colors.ON_SURFACE_VARIANT
    )
    def show_error(e="Something went wrong"):
        error_text.value = e
        page.open(error_message)
        page.update()

    #Settings components
    #Firebase
    def firebase_credentials_result(e: ft.FilePickerResultEvent):
        print("Selected files:", e.files)
        print("Selected file or directory:", e.path)
        if e.files:
            selected_firebase_text.value = f"Selected: {e.files[0].name}"
        else:
            selected_firebase_text.value = "No file selected."
        page.update()

    def updateSettingsJson(settings):
        try:
            with open(settings_path, "w") as file:
                json.dump(settings, file, indent=4)
        except Exception as e:
            show_error()

    def firebase_credentials_upload(e):
        try:
            upload_list = []
            if page.platform == "web":
                if firebase_credentials_picker.result != None and firebase_credentials_picker.result.files != None:
                    
                    upload_list.append(
                        FilePickerUploadFile(
                            firebase_credentials_picker.result.files[0].name,
                            upload_url=page.get_upload_url(settings_data["FirebaseCredentials"]["path"], 600),
                        )
                    )
                    firebase_credentials_picker.upload(upload_list)
            else:
                if firebase_credentials_picker.result and firebase_credentials_picker.result.files:
                    selected_file = firebase_credentials_picker.result.files[0]
                    src = selected_file.path  # local file path
                    dst = os.path.join(app_data_path,settings_data["FirebaseCredentials"]["path"])
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy(src, dst)
            if storage_bucket_input.value:
                settings_data["FirebaseCredentials"]["StorageBucket"] = storage_bucket_input.value
                updateSettingsJson(settings_data)

            reinitialize_firebase(settings_data["FirebaseCredentials"]["path"], settings_data["FirebaseCredentials"]["StorageBucket"])
            show_success()
            page.close(firebase_settings)
        except Exception as e:
            show_error()

    firebase_credentials_picker = ft.FilePicker(on_result=firebase_credentials_result)
    selected_firebase_text = ft.Text("No file selected.")
    page.overlay.append(firebase_credentials_picker)

    storage_bucket_input = ft.TextField(label="Storage bucket name", value=settings_data["FirebaseCredentials"]["StorageBucket"])
    firebase_settings = ft.AlertDialog(
        modal=True,
        title=ft.Text("Please upload the firebase credentials"),
        content=ft.Container(
            content=ft.Column([
                    ft.ElevatedButton("Choose file...",
                              on_click=lambda _: firebase_credentials_picker.pick_files(allow_multiple=False, allowed_extensions=["json"])),
                    selected_firebase_text,
                    storage_bucket_input
                ], tight=True),
            width=300,
            height=120,
            alignment=ft.alignment.center
        ),
        actions=[
            ft.TextButton("Upload", on_click=firebase_credentials_upload),
            ft.TextButton("Cancel", on_click=lambda e: page.close(firebase_settings)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        on_dismiss=lambda e: print("Modal dialog dismissed!"),
    )
    analysis_model_settings = ft.AlertDialog(
        modal=True,
        title=ft.Text("Please select an analysis model, the default value will be used"),
        content=ft.Text("Do you"),
        actions=[
            ft.TextButton("Save", on_click=lambda e: page.close(analysis_model_settings)),
            ft.TextButton("Cancel", on_click=lambda e: page.close(analysis_model_settings)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        on_dismiss=lambda e: print("Modal dialog dismissed!"),
    )
        
    page.title = "Litter analysis"
    app_bar = ft.AppBar(
        title=ft.Text("Litter analysis"),
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        actions=[
            ft.TextButton("Export camera results", on_click=lambda _: page.go("/")),
            ft.TextButton("Brand analysis", on_click=lambda _: page.go("/analysis")),
            ft.PopupMenuButton(
                content= ft.Container(
                            content=ft.Text("Settings"),
                            padding=ft.padding.only(right=10)
                        ),
                items=[
                    ft.PopupMenuItem(text="Firebase credentials", on_click=lambda e: page.open(firebase_settings)),
                    ft.PopupMenuItem(text="Litter",on_click=lambda e: page.open(analysis_model_settings)),
                ]
            ),
        ],
    )
    
    #Camera export view
    def update_textfield_from_picker(e, textfield):
        if e.control.value:
            textfield.value = e.control.value.strftime('%d-%m-%Y')
            textfield.error_text = None
            page.update() 
    def validate_date_input(date_input, datepicker):
        print(date_input.value)
        date_input.error_text = None
        try:
            datetime.strptime(date_input.value, "%d-%m-%Y")
            datepicker.value = datetime.strptime(date_input.value, "%d-%m-%Y")
            #print("Valid date typed:", date_input.value)
        except ValueError:
            date_input.error_text = "Invalid date format"
        page.update() 

    
    def set_export_path(e):
        export_folder_path.value = e.path
        page.update() 
        print(e.path)

    #Funtions to do Firebase stuff
    def export_from_firebase(e):
        startDate =  startdate_input.value.strip()
        endDate = enddate_input.value.strip()
        includeResults =  include_results.value
        includeAnnotatedImages =  include_annotated_images.value
        includeOriginalImages =  include_normal_images.value
        exportFolder = export_folder_path.value.strip()
        if not startDate or not endDate:
            show_error("Start and end date are required!")
            return

        if exportFolder == "No export folder selected.":
            show_error("Please select an export folder.")
            return
        if includeResults == False and includeAnnotatedImages == False and includeOriginalImages == False:
            show_error("Please select what to include in the export.")
            return
        page.run_task(get_data_from_firestore_and_storage, startDate, endDate, includeResults, includeAnnotatedImages, includeOriginalImages, exportFolder)

    async def get_firestore_results_to_excel(startDate, endDate, exportFolder):
        firebase_results_progress.visible = True
        firebase_results_progess_bar.value = None
        firebase_results_message.value = "Getting results..."
        page.update()
        try:
            data = []
            data_count = 0
            async for col in db.collections():
                    if col.id.endswith("objects"):
                        start_date = datetime.strptime(startDate, "%d-%m-%Y").replace(tzinfo=timezone.utc)
                        end_date = datetime.strptime(endDate, "%d-%m-%Y").replace(tzinfo=timezone.utc) + timedelta(days=1)
                        async for document in db.collection(col.id).where("end_timestamp", ">=", start_date).where("end_timestamp", "<", end_date).stream():
                            doc_dict = document.to_dict()
                            timestamp = doc_dict.get("end_timestamp")
                            if isinstance(timestamp, datetime):
                                doc_dict["Date"] = timestamp.date()
                                data.append(doc_dict)
                                data_count += 1
                                firebase_results_message.value = f"Fetched {data_count} objects"
                                page.update()
                            else:
                                print(f"⚠️ Missing or invalid timestamp in document: {document.id}")
                            page.update()
            if len(data) == 0:
                firebase_results_progess_bar.value = 1.0
                firebase_results_message.value = f"No Objects present"
                page.update()
                return
            print(data)
            firebase_results_message.value = f"Preparing for export to excel"
            page.update()
            results_df = pd.DataFrame(data)  
            results_df = results_df.groupby(["Date", "cls_name", "direction_y"]).size().reset_index(name="Total")
            results_df = results_df.rename(columns={"cls_name": "Type", "direction_y": "Direction"})
            total_row = {
                "Date": "",  # or empty string ""
                "Type": "",
                "Direction": "",
                "Total": results_df["Total"].sum()
            }

            results_df = pd.concat([results_df, pd.DataFrame([total_row])], ignore_index=True)
            firebase_results_message.value = f"Exporting to excel"
            page.update()
            results_df.to_excel(os.path.join(exportFolder, f"{startDate}_{endDate}.xlsx"), index=False)
            firebase_results_message.value = f"Exporting results complete"
            firebase_results_progess_bar.value = 1.0
            page.update()

        except Exception as e:
            print(e)
            show_error(e)
            firebase_results_progess_bar.value = 0.0
            firebase_results_message.value = "Something went wrong fetching the results"

    async def get_data_from_firestore_and_storage(startDate, endDate, includeResults, includeAnnotatedImages, includeOriginalImages, exportFolder):
        progress_container.visible = True
        firebase_results_progress.visible = False
        firebase_images_progress.visible = False
        firebase_annotated_progress.visible = False
        firebase_export_done.visible = False  
        page.update()  
        export_created_folder = os.path.join(exportFolder, f"export_{startDate}_{endDate}")
        os.makedirs(export_created_folder, exist_ok=True)
        tasks = []
        if includeResults:
            tasks.append(get_firestore_results_to_excel(startDate, endDate, export_created_folder))

        if includeAnnotatedImages:
            tasks.append(asyncio.to_thread(get_images_from_storage,startDate, endDate, "AnnotatedImages", export_created_folder))

        if includeOriginalImages:
            tasks.append(asyncio.to_thread(get_images_from_storage,startDate, endDate, "Images", export_created_folder))

        await asyncio.gather(*tasks)
        firebase_export_done.visible = True  
        firebase_export_done.value = f"The export is complete. You can find your files here: {export_created_folder}"
        page.update() 
    
    async def delete_firestore_results(startDate, endDate):
        firebase_results_progress.visible = True
        firebase_results_progess_bar.value = None
        firebase_results_message.value = "Deleting results..."
        page.update()
        try:
            data_count = 0
            batch = db.batch()
            async for col in db.collections():
                    if col.id.endswith("objects"):
                        start_date = datetime.strptime(startDate, "%d-%m-%Y").replace(tzinfo=timezone.utc)
                        end_date = datetime.strptime(endDate, "%d-%m-%Y").replace(tzinfo=timezone.utc) + timedelta(days=1)
                        async for document in db.collection(col.id).where("end_timestamp", ">=", start_date).where("end_timestamp", "<", end_date).stream():
                            batch.delete(document.reference)
                            data_count += 1
                            if data_count % 500 == 0:
                                await batch.commit() 
                                firebase_results_message.value = f"Deleted {data_count} objects"
                                page.update()
                                batch = db.batch()

            if data_count % 500 != 0:
                await batch.commit() 
            firebase_results_message.value = f"Deleting results complete"
            firebase_results_progess_bar.value = 1.0
            page.update()

        except Exception as e:
            print(e)
            show_error(e)


    async def delete_data_from_firestore_and_storage(startDate, endDate, includeResults, includeAnnotatedImages, includeOriginalImages, exportFolder):
        progress_container.visible = True
        firebase_results_progress.visible = False
        firebase_images_progress.visible = False
        firebase_annotated_progress.visible = False
        page.update()  
        tasks = []
        if includeResults:
            tasks.append(delete_firestore_results(startDate, endDate))

        await asyncio.gather(*tasks)
        firebase_export_done.visible = True  
        firebase_export_done.value = f"The data is deleted from firebase"
        page.update() 

    #Firebase Images
    def get_images_from_storage(startDate, endDate, type, exportFolder):
        try:
            if type == "AnnotatedImages":
                firebase_annotated_progress.visible = True
                firebase_annotated_images_progess_bar.value = None
                firebase_annotated_images_message.value = "Getting annotated images..."
            else:
                firebase_images_progress.visible = True
                firebase_original_images_progess_bar.value = None
                firebase_original_images_message.value = "Getting annotated images..."
            page.update()
            startDate = datetime.strptime(startDate, "%d-%m-%Y")
            endDate = datetime.strptime(endDate, "%d-%m-%Y")
            date_list = [
                (startDate + timedelta(days=i)).strftime("%d-%m-%Y")
                    for i in range((endDate - startDate).days + 1)
            ]
            grouped_list = defaultdict(list)
            for date_str in date_list:   
                for blob in gcs_bucket.list_blobs(match_glob=f"**/{type}/{date_str}/*.*"):
                    folder= blob.name.rsplit("/", 3)[0]
                    grouped_list[folder].append(blob.name.removeprefix(f'{folder}/'))
            for folder, blob_list in grouped_list.items():
                download_many_blobs_with_transfer_manager(type, "", "",folder, blob_list, exportFolder)
            if type == "AnnotatedImages":
                firebase_annotated_progress.visible = True
                firebase_annotated_images_progess_bar.value = 1.0
                firebase_annotated_images_message.value = "Annotated images complete"
            else:
                firebase_images_progress.visible = True
                firebase_original_images_progess_bar.value = 1.0
                firebase_original_images_message.value = "Images complete"
            page.update()
        except Exception as e:
            print("GCS access error:", e)
            if type == "AnnotatedImages":
                firebase_annotated_progress.visible = True
                firebase_annotated_images_progess_bar.value = 0.0
                firebase_annotated_images_message.value = "Something went wrong with the annotated images"
            else:
                firebase_images_progress.visible = True
                firebase_original_images_progess_bar.value = 0.0
                firebase_original_images_message.value = "Something went wrong with the images"
            page.update()
    
    def download_many_blobs_with_transfer_manager(type_images, progressBar, ProgressText, folder, blob_names, destination_directory="", workers=8):
        """Download blobs in a list by name, concurrently in a process pool.

        The filename of each blob once downloaded is derived from the blob name and
        the `destination_directory `parameter. For complete control of the filename
        of each blob, use transfer_manager.download_many() instead.

        Directories will be created automatically as needed to accommodate blob
        names that include slashes.
        """
        # The maximum number of processes to use for the operation. The performance
        # impact of this value depends on the use case, but smaller files usually
        # benefit from a higher number of processes. Each additional process occupies
        # some CPU and memory resources until finished. Threads can be used instead
        # of processes by passing `worker_type=transfer_manager.THREAD`.
        # workers=8
        transfer_manager.download_many_to_path(
            gcs_bucket, blob_names, destination_directory=destination_directory, max_workers=workers, blob_name_prefix=f"{folder}/",  worker_type=transfer_manager.THREAD
        )

        """for name, result in zip(blob_names, results):
            # The results list is either `None` or an exception for each blob in
            # the input list, in order.

            if isinstance(result, Exception):
                print("Failed to download {} due to exception: {}".format(name, result))
            else:
                print("Downloaded {} to {}.".format(name, destination_directory + name))"""

    def delete_from_firebase(e):
        startDate =  startdate_input.value.strip()
        endDate = enddate_input.value.strip()
        includeResults =  include_results.value
        includeAnnotatedImages =  include_annotated_images.value
        includeOriginalImages =  include_normal_images.value
        if not startDate or not endDate:
            show_error("Start and end date are required!")
            return
        if includeResults == False and includeAnnotatedImages == False and includeOriginalImages == False:
            show_error("Please select what to include in the export.")
            return
        page.run_task(delete_data_from_firestore_and_storage, startDate, endDate, includeResults, includeAnnotatedImages, includeOriginalImages)

    start_date_picker = ft.DatePicker(
            on_change=lambda e: update_textfield_from_picker(e, startdate_input),
         )
    page.overlay.append(start_date_picker)
    startdate_input = ft.TextField(
        label="Startdate",
        hint_text="DD-MM-YYYY",
        width=200,
        on_blur=lambda e: validate_date_input(startdate_input, start_date_picker),
    )
    end_date_picker = ft.DatePicker(            
            on_change=lambda e: update_textfield_from_picker(e, enddate_input),
        )
    page.overlay.append(end_date_picker)        
    enddate_input = ft.TextField(
        label="Enddate",
        hint_text="DD-MM-YYYY",
        width=200,
        on_blur=lambda e: validate_date_input(enddate_input, end_date_picker),
    )
    export_firebase_button = ft.ElevatedButton(text="Export",width=200, bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE, on_click=export_from_firebase)
    delete_firebase_button = ft.ElevatedButton(text="Delete", width=200 ,bgcolor=ft.Colors.RED,color=ft.Colors.WHITE, on_click=delete_from_firebase)
    include_results = ft.Checkbox(label="Include results", value=True)
    include_annotated_images = ft.Checkbox(label="Include annotated images", value=True)
    include_normal_images = ft.Checkbox(label="Include original images", value=False)
    firebase_export_folder_picker = ft.FilePicker(on_result=set_export_path)
    page.overlay.append(firebase_export_folder_picker)
    export_folder_path = ft.Text("No export folder selected.")

    firebase_results_message = ft.Text("Getting results...")
    firebase_results_progess_bar = ft.ProgressBar(width=500)
    firebase_results_progress = ft.Column([firebase_results_message, firebase_results_progess_bar])

    firebase_annotated_images_message = ft.Text("Getting annotated images...")
    firebase_annotated_images_progess_bar = ft.ProgressBar(width=500)
    firebase_annotated_progress = ft.Column([firebase_annotated_images_message, firebase_annotated_images_progess_bar])

    firebase_original_images_message = ft.Text("Getting original images...")
    firebase_original_images_progess_bar = ft.ProgressBar(width=500)
    firebase_images_progress = ft.Column([firebase_original_images_message, firebase_original_images_progess_bar])

    firebase_export_done = ft.Text("Export completed",weight=ft.FontWeight.BOLD, visible=False)

    progress_container = ft.Container(
                            expand=True,
                            visible=False,
                            alignment=ft.alignment.center,
                            padding=ft.padding.only( top=40),
                            content= ft.Container(
                                content=ft.Column(
                                    controls=[firebase_results_progress, firebase_annotated_progress, firebase_images_progress, firebase_export_done]

                                ),
                                width=500)
                            )
    
    #Brand AUDIT

    def set_audit_export_path(e):
        audit_export_folder_path.value = e.path
        page.update() 
    audit_export_folder_picker = ft.FilePicker(on_result=set_audit_export_path)
    page.overlay.append(audit_export_folder_picker)
    audit_export_folder_path = ft.Text("No export folder selected.")

    def set_audit_import_path(e):
        audit_import_folder_path.value = e.path
        page.update() 
    audit_import_folder_picker = ft.FilePicker(on_result=set_audit_import_path)
    page.overlay.append(audit_import_folder_picker)
    audit_import_folder_path = ft.Text("No brand audit folder selected.")


    brand_images_message = ft.Text("Analyzing images...")
    brand_progess_bar = ft.ProgressBar(width=500)
    brand_progress = ft.Column([brand_images_message, brand_progess_bar])

    brand_done = ft.Text("Export completed",weight=ft.FontWeight.BOLD, visible=False)

    progress_container_brand = ft.Container(
                            expand=True,
                            visible=False,
                            alignment=ft.alignment.center,
                            padding=ft.padding.only( top=40),
                            content= ft.Container(
                                content=ft.Column(
                                    controls=[brand_progress, brand_done]

                                ),
                                width=500)
                            )
    
    def run_classification(image, classification_model):
        result = classification_model(image, imgsz=224, verbose=False)[0]
        if result.probs is not None:
            #result.show()
            return result.names[int(result.probs.top1)],  [result.names[i] for i in result.probs.top5], result.probs.top5conf.cpu().numpy()
        else:
            return "unknown", [None, None, None, None, None], [None, None, None, None, None]

    def analyze_images(auditFolder, exportFolder):
        progress_container_brand.visible = True
        brand_done.visible = False
        brand_progress.visible = True
        brand_progess_bar.value = None
        brand_images_message.value = "Initialising models..."
        page.update()
        detection_model_path = settings_data["models"]["ObjectDetection"]["selected"]
        detection_model_standard_path = settings_data["models"]["ObjectDetection"]["default"]
        if detection_model_path and os.path.exists(os.path.join(app_data_path,detection_model_path)):
            detection_model = YOLO(os.path.join(app_data_path,detection_model_path))
        elif detection_model_standard_path and os.path.exists(os.path.join(app_data_path,detection_model_standard_path)):
            detection_model = YOLO(os.path.join(app_data_path,detection_model_standard_path))
        else:
            brand_progess_bar.value = 0
            brand_images_message.value = "No detection models present!"
            page.update()
            return
        
        classification_model_path = settings_data["models"]["Classification"]["selected"]
        classification_model_standard_path = settings_data["models"]["Classification"]["default"]
        if classification_model_path and os.path.exists(os.path.join(app_data_path,detection_model_path)):
            classification_model = YOLO(os.path.join(app_data_path,classification_model_path))
        elif classification_model_standard_path and os.path.exists(os.path.join(app_data_path,detection_model_standard_path)):
            classification_model = YOLO(os.path.join(app_data_path,classification_model_standard_path))
        else:
            brand_progess_bar.value = 0
            brand_images_message.value = "No classification models present!"
            page.update()
            return

        exts = ['.jpg', '.png', ".jpeg"]
        auditFolder = Path(auditFolder)
        exportFolder = Path(exportFolder)
        datename = datetime.today().strftime("%d-%m-%Y")
        exportFolder = os.path.join(exportFolder ,f"Brand_audit_{datename}")
        image_paths = [path for path in auditFolder.rglob('*') if path.suffix.lower() in exts]
        total_items = len(image_paths)
        item_count = 0
        results_list = []
        top5List = []
        brand_progess_bar.value = 0
        brand_images_message.value = f"Analysing {total_items} images..."
        page.update()

        batch_size = settings_data["models"]["batch_size"]
        for i in range(0, total_items, batch_size):
            batch = image_paths[i:i + batch_size]
            detection_results = detection_model(batch, stream=False, show_labels=False, imgsz=1024, conf=0.20, verbose=False)
            #print("generator", is_generator(detection_results))
            for result in detection_results:
                try:
                    if result is not None:
                        annotated_image = result.plot(labels=False, conf=False)
                        image = Path(result.path)
                        relative_parent = image.parent.relative_to(auditFolder)
                        destination_folder = os.path.join(exportFolder, "images",relative_parent)
                        os.makedirs(destination_folder, exist_ok=True)
                        shutil.copy2(result.path, os.path.join(destination_folder ,image.name))
                        for idx,((x1, y1, x2, y2), cls) in enumerate(zip(result.boxes.xyxy.cpu().numpy(), result.boxes.cls.cpu().numpy())):
                                x1, y1, x2, y2 = map(lambda v: int(round(v)), [x1, y1, x2, y2])
                                cropped_image = result.orig_img[y1:y2,x1:x2]
                                brand, top5, top5conf = run_classification(cropped_image, classification_model)  
                                label = f"{idx} - {result.names[int(cls)]} - {brand}"
                                font = cv2.FONT_HERSHEY_SIMPLEX
                                font_scale = 0.5
                                thickness = 1
                    
                                # Measure text size
                                (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
                                
                                # Adjust y position to avoid going off the top
                                label_y = max(y1 - text_height - baseline - 4, 0)
                                
                                # Draw filled background rectangle behind text
                                top_left = (x1, label_y)
                                bottom_right = (x1 + text_width + 1, label_y + text_height + baseline + 2)
                                
                                cv2.rectangle(annotated_image, top_left, bottom_right, (255, 255, 255), -1)
                                
                                # Put text (slightly inside the box to avoid touching the top)
                                cv2.putText(annotated_image, label, (x1, label_y + text_height), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)
                                results_list.append({
                                        'id': idx,
                                        'Image folder': str(relative_parent).replace("\\", "/"),
                                        'image_name': image.name,
                                        'Waste Type': result.names[int(cls)],
                                        'Brand': brand,
                                        'Box': (x1, y1, x2, y2),
                                        'original_img_path': str(image).replace("\\", "/")
                                })
                                top5_fields = {}
                                for i, (brand, conf) in enumerate(zip(top5, top5conf)):
                                    top5_fields[f'Brand {i + 1}'] = brand
                                    top5_fields[f'conf {i+1}'] = conf
                                top5List.append({
                                        'Image folder': str(relative_parent).replace("\\", "/"),
                                        'Image': image.name,
                                        'Object ID': idx,
                                        'Waste Type': result.names[int(cls)],
                                        **top5_fields,
                                        'original_img_path': str(image).replace("\\", "/")
                                })
                        destination_annotated_folder = os.path.join(exportFolder, "annotated",relative_parent)
                        os.makedirs(destination_annotated_folder, exist_ok=True)
                        cv2.imwrite(os.path.join(destination_annotated_folder ,image.name), annotated_image)
                except Exception as e:
                    print(f"Something went wrong: {e}")
                item_count += 1
                brand_images_message.value = f"Analysed {item_count} of {total_items} images"                               
                brand_progess_bar.value = item_count / total_items
                page.update()
        
        brand_images_message.value = f"Summarizing {item_count} images"
        brand_progess_bar.value = None
        page.update()
        results_df = pd.DataFrame(results_list)
        grouped = results_df.groupby(["Image folder", "Waste Type", "Brand"]).agg(
            Total=('id', 'size'),
            Images=('image_name', lambda x: list(set(x.dropna())))
        ).reset_index()
        grouped = grouped.sort_values(by='Image folder')
        top5_df = pd.DataFrame(top5List)
        excel_name  = os.path.join(exportFolder,f"Brand_audit_{datename}.xlsx")
        with pd.ExcelWriter(excel_name, engine='openpyxl') as writer:
            grouped.to_excel(writer, sheet_name='Brand audit', index=False)
            top5_df.to_excel(writer, sheet_name='Brands conf', index=False)

        brand_images_message.value = f"Summarized {item_count} images"
        brand_progess_bar.value = 1
        brand_done.value = f"You can find the export here: {exportFolder}"
        brand_done.visible = True
        page.update()
        
    async def start_analysis(auditFolder, exportFolder):
        await asyncio.to_thread(analyze_images, auditFolder, exportFolder)

    def analyse_brand_audit(e):
        exportFolder = audit_export_folder_path.value.strip()
        auditFolder = audit_import_folder_path.value.strip()
        if exportFolder == "No export folder selected.":
            show_error("Please select an export folder.")
            return
        if auditFolder == "No brand audit folder selected.":
            show_error("Please select a brand audit folder.")
            return
        page.run_task(start_analysis, auditFolder, exportFolder)


    analyse_brand_button = ft.ElevatedButton(text="Analyse brand audit", width=200, bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE, on_click=analyse_brand_audit)


    camera_view = ft.View(
        "/",
        appbar= app_bar,
        controls=
        [
            
            ft.Container(
                content=ft.Text("Export camera results",
                                size=40,
                                weight=ft.FontWeight.BOLD),
                alignment=ft.alignment.center
            ),
            ft.Container(
                alignment=ft.alignment.top_center,
                expand=True,
                padding=ft.padding.only( top=40),
                content= ft.Container(
                        width=500, 
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Container(
                                            content=ft.Row(
                                                        controls=[
                                                            startdate_input,
                                                            ft.IconButton(
                                                                icon=ft.Icons.CALENDAR_MONTH,
                                                                on_click=lambda e: page.open(start_date_picker)
                                                            )
                                                        ]
                                                    ),
                                        ),
                                        ft.Container(
                                            content=ft.Row(
                                                        controls=[
                                                            enddate_input,
                                                            ft.IconButton(
                                                                icon=ft.Icons.CALENDAR_MONTH,
                                                                on_click=lambda e: page.open(end_date_picker)
                                                            )
                                                        ]
                                                    ),
                                           
                                            
                                        )
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                ),
                                ft.Row(
                                    controls=[include_results,include_annotated_images, include_normal_images],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    
                                ),
                                ft.Row(
                                    controls=[ 
                                        ft.ElevatedButton("Choose file...",
                                            on_click=lambda _: firebase_export_folder_picker.get_directory_path(dialog_title="Result export location" )), export_folder_path],
                                    
                                ),
                                ft.Row(
                                    controls=[delete_firebase_button, export_firebase_button],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    
                                )

                            ],
                            spacing=30,
                            tight=True,
                            alignment=ft.MainAxisAlignment.START
                        ),
                        alignment=ft.alignment.top_center,
                    )
                ),
            progress_container
        ]
    )
    analysis_view = ft.View("/analysis", 
                            appbar= app_bar,
                            controls=
                            [         
                                app_bar,  
                                ft.Container(
                                    content=ft.Text("Brand Analysis",
                                                    size=40,
                                                    weight=ft.FontWeight.BOLD),
                                    alignment=ft.alignment.center
                                ),
                                ft.Container(
                                    alignment=ft.alignment.top_center,
                                    expand=True,
                                    padding=ft.padding.only( top=40),
                                    content= ft.Container(
                                            width=500, 
                                            content=ft.Column(
                                                controls=[
                                                    ft.Text("Brandaudit folder", weight=ft.FontWeight.BOLD,),
                                                    ft.Row(
                                                        controls=[ 
                                                            ft.ElevatedButton("Choose file...",
                                                                on_click=lambda _: audit_import_folder_picker.get_directory_path(dialog_title="Brand audit location" )), audit_import_folder_path],
                                                        
                                                        ),
                                                        ft.Text("Export folder", weight=ft.FontWeight.BOLD,),
                                                        ft.Row(
                                                        controls=[ 
                                                            ft.ElevatedButton("Choose file...",
                                                                on_click=lambda _: audit_export_folder_picker.get_directory_path(dialog_title="Brand audit export location" )), audit_export_folder_path],
                                                        
                                                        ),
                                                        ft.Row(
                                                            controls=[analyse_brand_button]
                                                            
                                                        )
                                                    ],
                                                    spacing=30
                                                )
                                            )
                                 )
                                ,progress_container_brand
                            ]
    )
    def route_change(route):
        print("test")
        page.views.clear()
           
        if page.route == "/analysis":
            page.views.append(
                analysis_view
            ) 
        else:
             page.views.append(
           camera_view
        )    
        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)


ft.app(main, upload_dir=app_data_path, )
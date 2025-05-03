import flet as ft
import os
import json
import shutil
from flet import FilePickerUploadFile
from datetime import datetime
import asyncio


app_data_path = os.getenv("FLET_APP_STORAGE_DATA")
settings_path = os.path.join(app_data_path, "settings.json")
try:
    with open(settings_path, "r") as file:
        settings_data = json.load(file)
except Exception as e:
    print("Failed to read JSON:", e)

def main(page: ft.Page):
    sucess_message = ft.SnackBar(
        duration="3000",
        content=ft.Text("✅ Upload successful!", color=ft.Colors.GREEN),
        bgcolor=ft.Colors.ON_SURFACE_VARIANT
    )
    def show_success():
        page.open(sucess_message)
        page.update()
        

    error_message = ft.SnackBar(
        duration="3000",
        content=ft.Text("Something went wrong", color=ft.Colors.RED),
        bgcolor=ft.Colors.ON_SURFACE_VARIANT
    )
    async def show_error():
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
            show_success()
            page.close(firebase_settings)
        except Exception as e:
            show_error()

    firebase_credentials_picker = ft.FilePicker(on_result=firebase_credentials_result)
    selected_firebase_text = ft.Text("No file selected.")
    page.overlay.append(firebase_credentials_picker)

    firebase_settings = ft.AlertDialog(
        modal=True,
        title=ft.Text("Please upload the firebase credentials"),
        content=ft.Container(
            content=ft.Column([
                    ft.ElevatedButton("Choose file...",
                              on_click=lambda _: firebase_credentials_picker.pick_files(allow_multiple=False, allowed_extensions=["json"])),
                    selected_firebase_text
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

    def handle_startdate_change(e):
        update_textfield_from_picker(e, startdate_input)
        

    def handle_startdate_dismissal(e):
        page.add(ft.Text(f"DatePicker dismissed"))

    
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
    

    camera_view = ft.View(
        "/",
        [
            app_bar,
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
                        width=800, 
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
                                            border=ft.border.only(right=ft.border.BorderSide(1, "black"))
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
                                )
                            ],
                            tight=True,
                            alignment=ft.MainAxisAlignment.START
                        ),
                        alignment=ft.alignment.top_center,
                    )
                )
        ]
    )
    def route_change(route):
        page.views.clear()
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


print(app_data_path)
ft.app(main, upload_dir=app_data_path)
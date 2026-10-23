import flet as ft

def main(page: ft.Page):
    counter = ft.Text("100", size=50, data=100)

    def increment_click(e: ft.Event[ft.FloatingActionButton]):
        counter.data += 1
        counter.value = str(counter.data)

    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD, key="increment", on_click=increment_click
    )
    page.add(
        ft.SafeArea(
            expand=True,
            content=ft.Container(
                content=counter,
                alignment=ft.Alignment.BOTTOM_CENTER,
            ),
        )
    )


if __name__ == "__main__":
    ft.run(main)

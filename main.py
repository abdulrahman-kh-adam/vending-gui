'''
CONNECTIONS BETWEEN PI AND ARDUINO
Pi <---> Ard
pin8  <---> pin0
pin10 <---> pin1
pin6  <---> GND

Note!
Arduino uses 5V logic and PI uses 3.3V Logic. Please consider using a logic
level shifter or a voltage divider to protect the Pi RX's pin
'''


import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import threading
import time
import random
import requests
from io import BytesIO

FontName = 'Segoe UI'
FontSize = 20
BackgroundColor = '#CCCCFF'

Ordertimer = 0
reminderTimer = 0
product_states = []
ordered_products = []
startOrderTime = 0
timeReminder = 0
current_order_id = None  # To store the order ID for payment
payment_check_active = False  # To control the payment status checking loop

# --- Fetch product data ONCE at startup ---
products_data = []

def fetch_products():
    global products_data
    show_notification("Loading products...", color="#FFA500", duration=10000)
    try:
        api_response = requests.get("https://mctasuvendingmachine.vercel.app/api/products")
        api_response.raise_for_status()
        products_data = [p for p in api_response.json()['data']['products'] if p['quantity'] > 0]
    except Exception as e:
        products_data = []
        print(f"Error loading products: {e}")
    hide_notification()
    root.after(0, populate_menu)

def populate_menu():
    for product in products_data:
        frame = ctk.CTkFrame(MenuPage, fg_color="#EFEFEF")
        frame.pack(pady=5, padx=10, fill='x')
        try:
            image_data = requests.get(product["imageUrl"]).content
            image = Image.open(BytesIO(image_data)).resize((50, 50))
        except:
            image = Image.new("RGB", (50, 50), color="gray")
        product_img = ctk.CTkImage(light_image=image, size=(50, 50))
        img_label = ctk.CTkLabel(frame, image=product_img, text="")
        img_label.image = product_img
        img_label.pack(side="left", padx=10)
        info = ctk.CTkLabel(frame, text=f'{product["name"]} - {product["price"]} LE', font=(FontName, 16), text_color="black")
        info.pack(side="left", padx=10)
        quantity_var = tk.IntVar(value=0)
        qty_frame = ctk.CTkFrame(frame, fg_color="transparent")
        qty_frame.pack(side="right", padx=10)
        create_qty_buttons(qty_frame, quantity_var)
        product_states.append({"data": product, "quantity": quantity_var})




# --- Core Functions ---

def Start():
    global Count, startOrderTime, Ordertimer
    if not Count > len(pages)-2:
        for page in mainPages:
            page.pack_forget()
        Count += 1
        page = mainPages[Count]
        page.pack(fill=ctk.BOTH, expand=True)
    startOrderTime = time.localtime().tm_min * 60 + time.localtime().tm_sec
    Ordertimer = start_timer(120, Restart)

def Restart():
    global Count, Count1, ordered_products, startOrderTime, timeReminder, current_order_id, payment_check_active
    paymentPage_lb2.configure(text='')
    startOrderTime = 0
    timeReminder = 0
    ordered_products = []
    current_order_id = None
    payment_check_active = False  # Stop any ongoing payment checks
    
    if not Count == 0:
        for page in mainPages:
            page.pack_forget()
        Count = 0
        page = mainPages[Count]
        page.pack(fill=tk.BOTH, expand=True)
    if not Count1 == 0:
        for page in pages:
            page.pack_forget()
        Count1 = 0
        page = pages[Count1]
        page.pack(fill=tk.BOTH, expand=True)
    for item in product_states:
        item["quantity"].set(0)

def start_timer(duration_sec, command):
    timer = threading.Timer(duration_sec, command)
    timer.start()
    return timer

def updatePaymentPage_lb2():
    global paymentPage_lb2, startOrderTime, timeReminder, reminderTimer
    timeReminder = 120 - (int(time.localtime().tm_min * 60 + time.localtime().tm_sec) - int(startOrderTime))
    paymentPage_lb2.configure(text=(str(timeReminder) + ' Sec'))
    paymentPage.after(1000, updatePaymentPage_lb2)

def check_payment_status():
    global current_order_id, payment_check_active
    if not payment_check_active or not current_order_id:
        return
    try:
        # Check order status
        response = requests.get(f"https://mctasuvendingmachine.vercel.app/api/orders/check-order-status/{current_order_id}")
        if response.ok:
            data = response.json().get('data', {})
            payment_status = data.get('paymentStatus', 'Pending')
            
            if payment_status == 'Paid':
                mark_order_done()
            else:
                root.after(1000, check_payment_status)
        else:
            print(f"Error checking payment status: {response.status_code} - {response.text}")
            root.after(1000, check_payment_status)
    except Exception as e:
        print(f"Exception while checking payment status: {str(e)}")
        root.after(1000, check_payment_status)

def mark_order_done():
    global current_order_id
    try:
        response = requests.get(f"https://mctasuvendingmachine.vercel.app/api/orders/mark-as-done/{current_order_id}")
        if response.ok:
            show_payment_success()
        else:
            print(f"Error marking order as done: {response.status_code} - {response.text}")
            show_payment_error("Failed to complete order")
    except Exception as e:
        print(f"Exception while marking order as done: {str(e)}")
        show_payment_error("Failed to complete order")

def show_notification(message, color="#333333", duration=3000):
    notification_frame.configure(fg_color=color)
    notification_label.configure(text=message)
    notification_frame.lift()
    notification_frame.place(relx=0.5, rely=0.1, anchor="center")
    root.update_idletasks()
    root.after(duration, hide_notification)
    
def hide_notification():
    notification_frame.place_forget()

def show_payment_success():
    show_notification("Payment Successful! Your order is being prepared.", color="#4CAF50", duration=3000)
    root.after(3000, Restart)

def show_payment_error(message):
    global payment_check_active
    payment_check_active = False
    show_notification(message, color="#F44336", duration=3000)
    root.after(3000, Restart)
def create_order():
    global current_order_id
    products = []
    total = 0
    for item in product_states:
        qty = item["quantity"].get()
        if qty > 0:
            product = item["data"].copy()
            product["quantity"] = qty
            total += product["price"] * qty
            products.append(product)
    if not products:
        Restart()
        return

    payload = {
        "products": products,
        "totalPrice": total
    }

    def order_thread():
        show_notification("Placing your order...", color="#FFA500", duration=10000)
        try:
            response = requests.post("https://mctasuvendingmachine.vercel.app/api/orders", json=payload)
            hide_notification()
            if response.ok:
                current_order_id = response.json().get('data', {}).get('order', {}).get('_id')
                root.after(0, moveToNextPage)
            else:
                show_notification("Order failed. Returning to home.", color="#F44336", duration=2000)
                root.after(2000, Restart)
        except Exception as e:
            hide_notification()
            show_notification(f"Error: {str(e)}", color="#F44336", duration=2000)
            root.after(2000, Restart)

    threading.Thread(target=order_thread).start()


def moveToNextPage():
    global Count1, payment_check_active
    if not Count1 > len(pages)-2:
        for page in pages:
            page.pack_forget()
        Count1 += 1
        if Count1 == 1:
            show_confirmation()
        if Count1 == 2:
            start_timer(1, updatePaymentPage_lb2)
            create_payment_request()  # Call payment API when payment page is shown
            payment_check_active = True
            check_payment_status()
        page = pages[Count1]
        page.pack(fill=tk.BOTH, expand=True)

def create_payment_request():
    global current_order_id
    if not current_order_id:
        print("Error: No order ID available for payment")
        show_payment_error("No order ID available")
        return

    products = []
    total = 0
    for item in product_states:
        qty = item["quantity"].get()
        if qty > 0:
            product = {
                "name": item["data"]["name"],
                "price": item["data"]["price"],
                "quantity": qty
            }
            total += item["data"]["price"] * qty
            products.append(product)

    payload = {
        "products": products,
        "total": total,
        "orderId": current_order_id
    }

    def payment_thread():
        show_notification("Generating QR Code...", color="#FFA500", duration=10000)
        try:
            response = requests.post("https://mctasuvendingmachine.vercel.app/api/payments/create-payment", json=payload)
            hide_notification()
            if response.ok:
                qr_url = response.json().get('data', {}).get('qr_url')
                if qr_url:
                    display_qr_from_url(qr_url)
                else:
                    show_payment_error("Payment service unavailable")
            else:
                show_payment_error("Payment service error")
        except Exception as e:
            hide_notification()
            show_payment_error("Payment service unavailable")

    threading.Thread(target=payment_thread).start()


def display_qr_from_url(url):
    try:
        response = requests.get(url, stream=True, timeout=5)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img = img.resize((200, 200), Image.LANCZOS)
            img_tk = ImageTk.PhotoImage(img)
            qr_label.config(image=img_tk)
            qr_label.image = img_tk
        else:
            raise Exception(f"Failed to download QR code: HTTP {response.status_code}")
    except Exception as e:
        print(f"Error displaying QR: {e}")
        show_payment_error("Failed to generate payment QR code")

def moveToBackPage():
    global Count1, payment_check_active
    payment_check_active = False
    if not Count1 == 0:
        for page in pages:
            page.pack_forget()
        Count1 -= 1
        page = pages[Count1]
        page.pack(fill=tk.BOTH, expand=True)

def show_confirmation():
    global ordered_products
    ordered_products = []
    for widget in ConfirmPage.winfo_children():
        if widget not in [ConfirmPage_lb, ConfirmNaviationFrame]:
            widget.destroy()
    total = 0.0
    any_selected = False
    scroll_frame = ctk.CTkScrollableFrame(ConfirmPage, fg_color="transparent", height=250)
    scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
    for item in product_states:
        qty = item["quantity"].get()
        if qty > 0:
            any_selected = True
            data = item["data"]
            name = data["name"]
            price = data["price"]
            image_path = data.get("imageUrl")
            line_total = qty * price
            total += line_total
            ordered_products.append(data.get("machineLocation"))
            ordered_products.append(qty)
            if image_path and image_path.startswith("http"):
                try:
                    response = requests.get(image_path, timeout=3)
                    img = Image.open(BytesIO(response.content)).resize((50, 50))
                except Exception:
                    img = Image.new("RGB", (50, 50), color="gray")
            else:
                img = Image.new("RGB", (50, 50), color="gray")
            img_ctk = ctk.CTkImage(light_image=img, size=(50, 50))
            item_frame = ctk.CTkFrame(scroll_frame, fg_color="#EFEFEF")
            item_frame.pack(fill="x", pady=5)
            img_label = ctk.CTkLabel(item_frame, image=img_ctk, text="")
            img_label.image = img_ctk
            img_label.pack(side="left", padx=10)
            info_text = f"{name} x {qty} = {line_total:.2f} LE"
            info_label = ctk.CTkLabel(item_frame, text=info_text, font=(FontName, 16), text_color="black")
            info_label.pack(side="left", padx=10)
    if any_selected:
        total_lbl = ctk.CTkLabel(ConfirmPage, text=f"Total: {total:.2f} LE",
                                 font=(FontName, 20, "bold"), text_color="black")
        total_lbl.pack(anchor="e", padx=30, pady=10)
    else:
        empty_lbl = ctk.CTkLabel(ConfirmPage, text="No items selected.",
                                 font=(FontName, 16), text_color="gray")
        empty_lbl.pack(pady=10)
    print(ordered_products)

def create_qty_buttons(frame, var):
    def increase():
        # Set all other quantities to 0
        for item in product_states:
            if item["quantity"] != var:
                item["quantity"].set(0)
        # Set the selected item's quantity to 1
        var.set(1)

    def decrease():
        var.set(0)

    minus_btn = ctk.CTkButton(frame, text="-", width=32, command=decrease)
    plus_btn = ctk.CTkButton(frame, text="+", width=32, command=increase)
    qty_lbl = ctk.CTkLabel(frame, textvariable=var, text_color="black")
    minus_btn.pack(side="left")
    qty_lbl.pack(side="left", padx=20)
    plus_btn.pack(side="left")

# ----- Main Window and Layout -----
root = ctk.CTk()
root.geometry('800x480')
root.title('GUI')

# Notification frame
notification_frame = ctk.CTkFrame(root, fg_color="#333333", corner_radius=10)
notification_label = ctk.CTkLabel(notification_frame, text="", font=(FontName, 16, "bold"), text_color="white", wraplength=700)
notification_label.pack(pady=15, padx=15)

# --- Home Page ---
HomePage = ctk.CTkFrame(master=root, fg_color=BackgroundColor)
HomePage_lb = ctk.CTkLabel(master=HomePage, text='Order.Pay.Go!', font=(FontName, FontSize), text_color="Black")
HomePage_lb.pack(expand=True, anchor="s", pady=20)
Start_btnFrame = ctk.CTkFrame(master=HomePage, fg_color='transparent')
Start_btn = ctk.CTkButton(
    master=Start_btnFrame, width=120, height=40, corner_radius=20,
    border_width=2, border_color='#4285F4', text='Order Now',
    font=(FontName, FontSize), text_color='#1877f2',
    fg_color=BackgroundColor, hover_color='#D9D9FF',
    command=Start
)
Start_btn.pack(side=ctk.LEFT, padx=10)
Start_btnFrame.pack(side=ctk.BOTTOM, pady=10)

HomePage.pack(fill=ctk.BOTH, expand=True)

# --- Main frame ---
mainFrame = ctk.CTkFrame(master=root, fg_color=BackgroundColor)

# --- Menu Page ---
MenuPage = ctk.CTkScrollableFrame(master=mainFrame, fg_color='transparent')
MenuPage_lb = ctk.CTkLabel(master=MenuPage, text='Menu', font=(FontName, FontSize))
MenuPage_lb.pack()

# Populate Menu with single-time fetched data
for product in products_data:
    frame = ctk.CTkFrame(MenuPage, fg_color="#EFEFEF")
    frame.pack(pady=5, padx=10, fill='x')
    # Try loading product image from URL or use gray fallback
    try:
        image_data = requests.get(product["imageUrl"]).content
        image = Image.open(BytesIO(image_data)).resize((50, 50))
    except:
        image = Image.new("RGB", (50, 50), color="gray")
    product_img = ctk.CTkImage(light_image=image, size=(50, 50))
    img_label = ctk.CTkLabel(frame, image=product_img, text="")
    img_label.image = product_img
    img_label.pack(side="left", padx=10)
    info = ctk.CTkLabel(frame, text=f'{product["name"]} - {product["price"]} LE', font=(FontName, 16), text_color="black")
    info.pack(side="left", padx=10)
    quantity_var = tk.IntVar(value=0)
    qty_frame = ctk.CTkFrame(frame, fg_color="transparent")
    qty_frame.pack(side="right", padx=10)
    create_qty_buttons(qty_frame, quantity_var)
    product_states.append({"data": product, "quantity": quantity_var})

MenuPage.pack(fill=tk.BOTH, expand=True)

# --- Confirm Page ---
ConfirmPage = ctk.CTkFrame(master=mainFrame, fg_color='transparent')
ConfirmPage_lb = ctk.CTkLabel(master=ConfirmPage, text='You ordered', font=(FontName, FontSize))
ConfirmPage_lb.pack()

# --- Payment Page ---
paymentPage = ctk.CTkFrame(master=mainFrame, fg_color='transparent')
paymentPage_lb = ctk.CTkLabel(master=paymentPage, corner_radius=10,
                             text='Scan The QR Code To Get Your Order(:',
                             font=(FontName, 40), text_color="black")
paymentPage_lb.pack(pady=20)
paymentPage_lb1 = ctk.CTkLabel(master=paymentPage,
                             text='Your order will expire within',
                             font=(FontName, 16), text_color="gray")
paymentPage_lb1.pack(pady=10)
paymentPage_lb2 = ctk.CTkLabel(master=paymentPage,
                             text='',
                             font=(FontName, 16), text_color="gray")
paymentPage_lb2.pack(pady=10)
qr_label = tk.Label(master=paymentPage, bg="white")
qr_label.pack(expand=True, anchor="center")

# --- Pages Setup ---
mainPages = [HomePage, mainFrame]
Count = 0
pages = [MenuPage, ConfirmPage, paymentPage]
Count1 = 0

# --- Navigation Buttons ---

Buttons_hover_color = '#D9D9FF'
Buttons_text_color = '#1877f2'

# Menu page Navigation
MenuNaviationFrame = ctk.CTkFrame(master=MenuPage, fg_color='transparent')
next_btn = ctk.CTkButton(
    master=MenuNaviationFrame, text='Submit',
    font=(FontName, FontSize), height=30, text_color=Buttons_text_color,
    fg_color=BackgroundColor, hover_color=Buttons_hover_color, command=moveToNextPage
)
next_btn.pack(side=ctk.RIGHT, padx=10, pady=10)
Cancle_btn = ctk.CTkButton(
    master=MenuNaviationFrame, text='Cancel',
    font=(FontName, FontSize), height=30, text_color=Buttons_text_color,
    fg_color=BackgroundColor, hover_color=Buttons_hover_color, command=Restart
)
Cancle_btn.pack(side=ctk.LEFT, padx=20, pady=10)
MenuNaviationFrame.pack(side=ctk.BOTTOM, pady=10, padx=10)

# Confirm page Navigation
ConfirmNaviationFrame = ctk.CTkFrame(master=ConfirmPage, fg_color='transparent')
back_btn = ctk.CTkButton(
    master=ConfirmNaviationFrame, text='Back',
    font=(FontName, FontSize), height=30, text_color=Buttons_text_color,
    fg_color=BackgroundColor, hover_color=Buttons_hover_color, command=moveToBackPage
)
back_btn.pack(side=ctk.LEFT, padx=10, pady=10)
comfirm_btn = ctk.CTkButton(
    master=ConfirmNaviationFrame, text='Confirm',
    font=(FontName, FontSize), height=30, text_color='#1877f2',
    fg_color=BackgroundColor, hover_color=Buttons_hover_color,
    command=create_order
)
comfirm_btn.pack(side=ctk.RIGHT, padx=10, pady=10)
Cancle_btn2 = ctk.CTkButton(
    master=ConfirmNaviationFrame, text='Cancel',
    font=(FontName, FontSize), height=30, text_color=Buttons_text_color,
    fg_color=BackgroundColor, hover_color=Buttons_hover_color, command=Restart
)
Cancle_btn2.pack(side=ctk.LEFT, padx=20, pady=10)
ConfirmNaviationFrame.pack(side=ctk.BOTTOM, pady=10, padx=10)

# Start product fetching thread
threading.Thread(target=fetch_products).start()

root.mainloop()

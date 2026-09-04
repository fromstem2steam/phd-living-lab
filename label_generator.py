import io
import qrcode
from PIL import Image, ImageDraw, ImageFont

def generate_lab_label(
    product_name: str,
    crop_name: str,
    pod_id: str,
    wall_section: str,
    batch_id: str,
    order_id: str = "N/A",
    app_qr_url: str = "https://your-kiosk.streamlit.app"
) -> bytes:
    width, height = 600, 350
    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)

    # Frame & Banners
    draw.rectangle([(10, 10), (width - 10, height - 10)], outline="black", width=3)
    draw.rectangle([(15, 15), (width - 15, 55)], fill="black")
    draw.line([(15, 230), (width - 15, 230)], fill="black", width=2)

    try:
        font_header = ImageFont.truetype("arial.ttf", 20)
        font_title = ImageFont.truetype("arial.ttf", 22)
        font_body = ImageFont.truetype("arial.ttf", 16)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except IOError:
        font_header = font_title = font_body = font_small = ImageFont.load_default()

    draw.text((25, 22), "SMC LIVING LAB | AGTECH DIAGNOSTIC", fill="white", font=font_header)
    draw.text((25, 70), f"SPECIMEN: {product_name.upper()}", fill="black", font=font_title)
    draw.text((25, 105), f"CROP CULTIVAR: {crop_name}", fill="black", font=font_body)
    draw.text((25, 135), f"ORIGIN POD: {pod_id}", fill="black", font=font_body)
    draw.text((25, 165), f"WALL SECTION: {wall_section}", fill="black", font=font_body)
    draw.text((25, 195), f"BATCH REF: #{batch_id[:12]}", fill="black", font=font_small)

    # QR Code Generation
    target_url = f"{app_qr_url}/?order_id={order_id}&pod_id={pod_id}"
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(target_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB").resize((150, 150))
    
    image.paste(qr_img, (420, 65))
    draw.text((435, 212), "SCAN FOR LIVE ORIGIN", fill="black", font=font_small)

    draw.text((25, 240), f"ORDER ID: {order_id[:12]}", fill="black", font=font_small)
    draw.text((25, 260), "EIMTA TELEMETRY VERIFIED | GDPR COMPLIANT LOG", fill="black", font=font_small)
    draw.text((25, 280), "STEAM-NET™ PATHWAY 1: BIO-LOOPS & AGTECH", fill="black", font=font_small)
    draw.text((25, 305), "MALTA LIVING INNOVATION LABS PILOT", fill="black", font=font_small)

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()

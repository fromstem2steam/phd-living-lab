import uuid
import pandas as pd
import plotly.express as px
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Living Lab Admin Console", layout="wide")


@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


supabase = init_supabase()


def upload_image_to_supabase(uploaded_file):
    if uploaded_file is None:
        return None

    # Generate a unique file path to prevent overwriting existing files
    file_ext = uploaded_file.name.split(".")[-1]
    file_path = f"items/{uuid.uuid4()}.{file_ext}"
    file_bytes = uploaded_file.getvalue()

    # Upload to 'product-images' bucket
    supabase.storage.from_("product-images").upload(
        path=file_path,
        file=file_bytes,
        file_options={"content-type": uploaded_file.type},
    )

    # Retrieve public URL
    return supabase.storage.from_("product-images").get_public_url(file_path)


st.title("⚙️ Living Lab Master Administration")

tab1, tab2, tab3, tab4 = st.tabs([
    "🛍️ Retail Inventory",
    "🌱 AgTech & Wall Grid",
    "🪴 Plant Health & Growth",
    "📊 Telemetry & PhD Metrics",
])

# -------------------------------------------------------------
# TAB 1: RETAIL INVENTORY MANAGEMENT
# -------------------------------------------------------------
with tab1:
    st.subheader("In-Stock Retail Inventory")
    items = (
        supabase.schema("ordering")
        .table("retail_inventory")
        .select("*")
        .order("name")
        .execute()
        .data
    )

    if items:
        df = pd.DataFrame(items)
        # Display image_url column if present in dataframe
        display_cols = [
            col
            for col in [
                "sku",
                "name",
                "price",
                "stock_quantity",
                "image_url",
                "is_active",
            ]
            if col in df.columns
        ]
        st.dataframe(
            df[display_cols],
            use_container_width=True,
        )

        st.divider()
        st.subheader("Quick Stock Adjustment")
        c1, c2, c3 = st.columns(3)
        selected_item = c1.selectbox(
            "Select Product",
            options=items,
            format_func=lambda x: f"{x['name']} (SKU: {x['sku']})",
        )
        new_qty = c2.number_input(
            "New Stock Quantity",
            value=selected_item["stock_quantity"],
            min_value=0,
        )

        if c3.button("Update Stock"):
            (
                supabase.schema("ordering")
                .table("retail_inventory")
                .update({"stock_quantity": new_qty})
                .eq("id", selected_item["id"])
                .execute()
            )
            st.success(f"Updated {selected_item['name']} stock to {new_qty}!")
            st.rerun()
    else:
        st.info("No retail products registered yet.")

    st.divider()
    st.subheader("Register New Product")
    with st.form("new_product_form"):
        sku = st.text_input("SKU (e.g., BOT-EXT-01)")
        name = st.text_input(
            "Product Name (e.g., Botanical Extraction Tonic)"
        )
        desc = st.text_area("Description")
        price = st.number_input(
            "Price (€)", min_value=0.0, value=12.50, step=0.50
        )
        stock = st.number_input("Initial Stock Quantity", min_value=0, value=20)
        uploaded_image = st.file_uploader(
            "Product Image", type=["png", "jpg", "jpeg", "webp"]
        )

        if st.form_submit_button("Save Product") and sku and name:
            image_url = None
            if uploaded_image:
                image_url = upload_image_to_supabase(uploaded_image)

            qr_id = f"ITEM-{sku}"
            (
                supabase.schema("ordering")
                .table("retail_inventory")
                .insert({
                    "sku": sku,
                    "name": name,
                    "description": desc,
                    "price": price,
                    "stock_quantity": stock,
                    "qr_code_id": qr_id,
                    "image_url": image_url,
                    "is_active": True,
                })
                .execute()
            )
            st.success(f"Product '{name}' created with image!")
            st.rerun()

# -------------------------------------------------------------
# TAB 2: AGTECH CROP BATCHES & WALL GRID ASSIGNMENTS
# -------------------------------------------------------------
with tab2:
    st.subheader("Hydroponic Crop Batch Management")
    locations = (
        supabase.schema("hydroponics")
        .table("wall_locations")
        .select("id")
        .execute()
        .data
    )
    loc_opts = [l["id"] for l in locations] if locations else []

    with st.form("batch_form"):
        crop_name = st.text_input("Crop Name (e.g., Genovese Basil)")
        selected_loc = st.selectbox("Assign to Wall Grid Pod", loc_opts)

        if st.form_submit_button("Register Active Harvest Batch") and crop_name:
            (
                supabase.schema("hydroponics")
                .table("crop_batches")
                .insert({
                    "crop_name": crop_name,
                    "location_id": selected_loc,
                    "is_active_harvest": True,
                })
                .execute()
            )
            st.success(
                f"Batch '{crop_name}' assigned to pod {selected_loc}!"
            )
            st.rerun()

    st.divider()
    st.subheader("Active Wall Batches")
    active_batches = (
        supabase.schema("hydroponics")
        .table("crop_batches")
        .select("*")
        .eq("is_active_harvest", True)
        .execute()
        .data
    )
    if active_batches:
        st.dataframe(
            pd.DataFrame(active_batches)[
                ["crop_name", "location_id", "planted_at"]
            ],
            use_container_width=True,
        )

# -------------------------------------------------------------
# TAB 3: PLANT HEALTH INSPECTIONS & GROWTH TRACKING
# -------------------------------------------------------------
with tab3:
    st.subheader("🪴 Plant Health & Growth Stage Tracker")
    batches = (
        supabase.schema("hydroponics")
        .table("crop_batches")
        .select("id, crop_name, location_id")
        .eq("is_active_harvest", True)
        .execute()
        .data
    )

    col_log, col_viz = st.columns([1, 1])

    with col_log:
        st.markdown("### Log Health Inspection")
        if not batches:
            st.info(
                "No active crop batches found. Register a batch in Tab 2 first."
            )
        else:
            with st.form("health_inspection_form"):
                selected_batch = st.selectbox(
                    "Select Crop Batch",
                    options=batches,
                    format_func=lambda x: f"{x['crop_name']} (Pod: {x['location_id']})",
                )

                growth_stage = st.selectbox(
                    "Growth Stage",
                    ["Germination", "Seedling", "Vegetative", "Harvest-Ready"],
                )
                health_score = st.slider(
                    "Overall Health Rating (1-10)", 1, 10, 8
                )
                canopy_height = st.number_input(
                    "Canopy Height (cm)", min_value=0.0, value=5.0, step=0.5
                )
                leaf_condition = st.selectbox(
                    "Leaf Condition",
                    [
                        "Healthy Green",
                        "Yellowing (Chlorosis)",
                        "Tip Burn",
                        "Wilting",
                    ],
                )
                pest_status = st.selectbox(
                    "Pest/Disease Status",
                    [
                        "None",
                        "Aphids",
                        "Spider Mites",
                        "Algae Build-up",
                        "Root Rot",
                    ],
                )
                notes = st.text_area("Inspection Notes / Remediation Taken")
                inspector = st.text_input(
                    "Inspector Name / Youth ID", value="Youth Cohort #1"
                )

                if st.form_submit_button("Submit Health Log 📝"):
                    (
                        supabase.schema("hydroponics")
                        .table("plant_health_logs")
                        .insert({
                            "batch_id": selected_batch["id"],
                            "growth_stage": growth_stage,
                            "health_score": health_score,
                            "canopy_height_cm": canopy_height,
                            "leaf_color_index": leaf_condition,
                            "pest_disease_status": pest_status,
                            "notes": notes,
                            "logged_by": inspector,
                        })
                        .execute()
                    )
                    st.success(
                        f"Health log saved for {selected_batch['crop_name']}!"
                    )
                    st.rerun()

    with col_viz:
        st.markdown("### Growth Trajectory & Health Analytics")
        if batches:
            view_batch = st.selectbox(
                "Filter Visuals by Batch",
                options=batches,
                format_func=lambda x: f"{x['crop_name']} ({x['location_id']})",
                key="viz_batch_select",
            )

            logs = (
                supabase.schema("hydroponics")
                .table("plant_health_logs")
                .select("*")
                .eq("batch_id", view_batch["id"])
                .order("created_at")
                .execute()
                .data
            )

            if logs:
                df_logs = pd.DataFrame(logs)
                fig_height = px.line(
                    df_logs,
                    x="created_at",
                    y="canopy_height_cm",
                    title=f"Height Trajectory (cm) - {view_batch['crop_name']}",
                    markers=True,
                )
                st.plotly_chart(fig_height, use_container_width=True)

                latest_log = df_logs.iloc[-1]
                st.metric(
                    "Latest Health Score",
                    f"{latest_log['health_score']}/10",
                    delta=f"Stage: {latest_log['growth_stage']}",
                )
                if latest_log["pest_disease_status"] != "None":
                    st.warning(f"Alert: {latest_log['pest_disease_status']}")
                else:
                    st.success("No pests or diseases detected.")
            else:
                st.info("No health records logged for this batch yet.")

# -------------------------------------------------------------
# TAB 4: TELEMETRY LOGS & PHD METRICS PIPELINE
# -------------------------------------------------------------
with tab4:
    st.subheader("AgTech Water Telemetry Logs")
    telemetry_data = (
        supabase.schema("hydroponics")
        .table("telemetry_logs")
        .select("*")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
        .data
    )

    if telemetry_data:
        tdf = pd.DataFrame(telemetry_data)
        latest = tdf.iloc[0]
        m1, m2, m3 = st.columns(3)
        m1.metric("pH Level", f"{latest['ph']}")
        m2.metric("EC (mS/cm)", f"{latest['ec']}")
        m3.metric("Water Temp (°C)", f"{latest['water_temp']}")

        fig = px.line(
            tdf,
            x="created_at",
            y=["ph", "ec", "water_temp"],
            title="Sensors Trajectory Over Time",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No telemetry logs received yet.")

    st.divider()
    st.subheader("WordPress Capability Progression Logs (PhD Data)")
    training_data = (
        supabase.schema("training")
        .table("module_completions")
        .select("*")
        .execute()
        .data
    )
    if training_data:
        st.dataframe(pd.DataFrame(training_data), use_container_width=True)
    else:
        st.info("No training completions synced yet from WordPress.")

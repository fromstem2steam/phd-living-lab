from streamlit_autorefresh import st_autorefresh

# Refresh every 5000 milliseconds (5 seconds)
st_autorefresh(interval=5000, key="datarefresh")


import streamlit as st
from supabase import create_client
from label_generator import generate_lab_label

st.set_page_config(page_title="Kitchen Display System", layout="wide")


@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


supabase = init_supabase()

st.title("🍳 Kitchen Display System & Label Station")

orders = (
    supabase.schema("ordering")
    .table("orders")
    .select("*")
    .in_("status", ["pending", "preparing"])
    .order("created_at")
    .execute()
    .data
)

if orders:
    cols = st.columns(3)
    for idx, order in enumerate(orders):
        with cols[idx % 3]:
            with st.container(border=True):
                st.subheader(f"Order #{order['id'][:8]}")
                st.write(f"**Status:** {order['status'].upper()}")

                # Fetch order line items
                items = (
                    supabase.schema("ordering")
                    .table("order_items")
                    .select("menu_items(name), retail_inventory(name)")
                    .eq("order_id", order["id"])
                    .execute()
                    .data
                )
                for i in items:
                    name = (
                        i["menu_items"]["name"]
                        if i["menu_items"]
                        else i["retail_inventory"]["name"]
                    )
                    st.write(f"- {name}")

                if order["status"] == "pending":
                    if st.button("Start Prep 👨‍🍳", key=f"p_{order['id']}"):
                        supabase.schema("ordering").table("orders").update(
                            {"status": "preparing"}
                        ).eq("id", order["id"]).execute()
                        st.rerun()
                elif order["status"] == "preparing":
                    if st.button("Mark Ready ✅", key=f"r_{order['id']}"):
                        supabase.schema("ordering").table("orders").update(
                            {"status": "ready"}
                        ).eq("id", order["id"]).execute()
                        st.rerun()

                # Print Lab Label Button
                if st.button("🏷️ Print Lab Label", key=f"lbl_{order['id']}"):
                    origins = (
                        supabase.rpc(
                            "get_order_all_origins",
                            {"target_order_id": order["id"]},
                        )
                        .execute()
                        .data
                    )
                    if origins:
                        for orig in origins:
                            png = generate_lab_label(
                                orig["product_name"],
                                orig["crop_name"],
                                orig["location_id"],
                                orig["wall_section"],
                                "BATCH-2027",
                                order["id"],
                            )
                            st.image(png, width=250)
                            st.download_button(
                                "Download PNG",
                                png,
                                f"label_{orig['product_name']}.png",
                                "image/png",
                                key=f"dl_{orig['product_name']}",
                            )

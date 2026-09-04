import streamlit as st
from supabase import create_client
st.set_page_config(page_title="Living Lab Café Kiosk", layout="wide")
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
supabase = init_supabase()
# Parse URL parameters
table_id = st.query_params.get("table_id", 1)
scanned_sku = st.query_params.get("item_sku", None)
if "active_order_id" not in st.session_state:
    st.session_state.active_order_id = None
if "cart" not in st.session_state:
    st.session_state.cart = []

# Handle shelf QR scans
if scanned_sku and "scanned_added" not in st.session_state:
    r_item = supabase.table("retail_inventory").schema("ordering").select("*").eq("sku", scanned_sku).gt("stock_quantity", 0).execute().data
    if r_item:
        st.session_state.cart.append({"id": r_item[0]["id"], "name": r_item[0]["name"], "price": r_item[0]["price"], "is_retail": True})
        st.session_state.scanned_added = True
        st.toast(f"Added {r_item[0]['name']} via QR Code!")

@st.fragment(run_every=5)
def render_live_order_status(order_id):
    order = supabase.table("orders").schema("ordering").select("*").eq("id", order_id).execute().data[0]
    st.subheader(f"📍 Order #{order['id'][:8]} Status: {order['status'].upper()}")
    
    # Render Mapped Hydroponic Origin
    origins = supabase.rpc("get_order_all_origins", {"target_order_id": order_id}).execute().data
    if origins:
        st.subheader("🌱 Farm-to-Table Wall Origin Map")
        for orig in origins:
            st.success(f"**{orig['product_name']}** uses **{orig['crop_name']}** from **{orig['wall_section']}**")
            for r in range(1, 4):
                cols = st.columns(3)
                for c in range(1, 4):
                    if r == orig["row_num"] and c == orig["col_num"]:
                        cols[c-1].markdown(f"🟢 **[{orig['crop_name']}]**")
                    else:
                        cols[c-1].markdown(f"⚪ Pod R{r}-C{c}")

if st.session_state.active_order_id:
    render_live_order_status(st.session_state.active_order_id)
else:
    st.title(f"🌿 Living Lab Café (Table {table_id})")
    tab1, tab2 = st.tabs(["🍽️ Café Menu", "🛍️ In-Stock Retail"])

    with tab1:
        items = supabase.table("menu_items").schema("ordering").select("*").eq("is_available", True).execute().data
        for i in items:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{i['name']}** ({i['category']})")
            c2.write(f"€{i['price']:.2f}")
            if c3.button("Add", key=f"m_{i['id']}"):
                st.session_state.cart.append({"id": i["id"], "name": i["name"], "price": i["price"], "is_retail": False})

    with tab2:
        r_items = supabase.table("retail_inventory").schema("ordering").select("*").gt("stock_quantity", 0).execute().data
        for r in r_items:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{r['name']}** (Stock: {r['stock_quantity']})")
            c2.write(f"€{r['price']:.2f}")
            if c3.button("Add", key=f"r_{r['id']}"):
                st.session_state.cart.append({"id": r["id"], "name": r["name"], "price": r["price"], "is_retail": True})

    st.divider()
    st.subheader("🛒 Current Selection")
    if st.session_state.cart:
        total = sum(i["price"] for i in st.session_state.cart)
        for i in st.session_state.cart:
            st.write(f"- {i['name']} (€{i['price']:.2f})")
        st.write(f"**Total: €{total:.2f}**")
        
        if st.button("Submit & Pay Order 🚀", type="primary"):
            new_ord = supabase.table("orders").schema("ordering").insert({"table_id": int(table_id), "total_amount": float(total)}).execute().data[0]
            for item in st.session_state.cart:
                payload = {"order_id": new_ord["id"]}
                if item["is_retail"]:
                    payload["retail_item_id"] = item["id"]
                else:
                    payload["menu_item_id"] = item["id"]
                supabase.table("order_items").schema("ordering").insert(payload).execute()
            st.session_state.active_order_id = new_ord["id"]
            st.session_state.cart = []
            st.rerun()

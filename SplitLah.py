import streamlit as st
import requests
import os
import json
import bcrypt

# =========================
# 🔐 USER AUTHENTICATION
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_FILE = os.path.join(BASE_DIR, "users.json")


# --- Hashing ---
def hash_password(password: str) -> str:
    pw = password.encode("utf-8")
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def is_bcrypt_hash(s: str) -> bool:
    return isinstance(s, str) and s.startswith("$2b$") and len(s) > 50


# --- JSON I/O ---
def load_users():
    if not os.path.exists(USER_FILE):
        with open(USER_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": []}, f)
    with open(USER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["users"]


def save_users(users):
    for u in users:
        if not is_bcrypt_hash(u.get("password", "")):
            raise ValueError(
                f"❌ Refusing to save raw password for user '{u.get('username')}'. Hash it first!"
            )
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": users}, f, indent=4)


def get_user(username):
    users = load_users()
    for u in users:
        if u["username"].lower() == username.lower():
            return u
    return None


def update_user_groups(username, groups):
    users = load_users()
    for u in users:
        if u["username"].lower() == username.lower():
            u["groups"] = groups
    save_users(users)


def update_user_plan(username, plan_type, plan_duration):
    users = load_users()
    for u in users:
        if u["username"].lower() == username.lower():
            u["plan_type"] = plan_type
            u["plan_duration"] = plan_duration
    save_users(users)


def user_exists(username: str) -> bool:
    users = load_users()
    return any(u["username"].lower() == username.lower() for u in users)


def create_user(username: str, password: str, plan_type="Basic", plan_duration="Monthly"):
    users = load_users()
    if user_exists(username):
        return False
    hashed_pw = hash_password(password)
    users.append(
        {
            "username": username,
            "password": hashed_pw,
            "groups": {},
            "plan_type": plan_type,
            "plan_duration": plan_duration,
        }
    )
    save_users(users)
    return True


def verify_user(username: str, password: str):
    users = load_users()
    for u in users:
        if u["username"].lower() == username.lower():
            if verify_password(password, u["password"]):
                return u["username"]
    return None


# =========================
# 🧠 SESSION STATE SETUP
# =========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "login_username" not in st.session_state:
    st.session_state.login_username = ""
if "login_password" not in st.session_state:
    st.session_state.login_password = ""
if "signup_username" not in st.session_state:
    st.session_state.signup_username = ""
if "signup_password" not in st.session_state:
    st.session_state.signup_password = ""

# App defaults
if "page" not in st.session_state:
    st.session_state.page = "plan_selection"
if "plan_type" not in st.session_state:
    st.session_state.plan_type = "Basic"
if "plan_duration" not in st.session_state:
    st.session_state.plan_duration = "Monthly"
if "budget_remaining" not in st.session_state:
    st.session_state.budget_remaining = 0.0
if "budget_set" not in st.session_state:
    st.session_state.budget_set = 0.0
if "loop_active" not in st.session_state:
    st.session_state.loop_active = False
if "show_split_results" not in st.session_state:
    st.session_state.show_split_results = False

# =========================
# 🔑 LOGIN / SIGN-UP PAGE
# =========================
if not st.session_state.logged_in:
    st.title("🔐 SplitLah Login")

    choice = st.radio("Select an option:", ["Login", "Create Account"])

    if choice == "Login":
        st.text_input("Username", key="login_username")
        st.text_input("Password", type="password", key="login_password")

        if st.button("Login"):
            username = st.session_state.login_username.strip()
            password = st.session_state.login_password
            if not username or not password:
                st.warning("⚠️ Please fill in all fields.")
            else:
                name = verify_user(username, password)
                if name:
                    st.session_state.logged_in = True
                    st.session_state.user_name = name
                    # load user's plan into session
                    ud = get_user(name)
                    if ud:
                        st.session_state.plan_type = ud.get("plan_type", "Basic")
                        st.session_state.plan_duration = ud.get("plan_duration", "Monthly")
                        st.session_state.groups = ud.get("groups", {})
                    st.success(f"✅ Welcome back, {name}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password.")

    elif choice == "Create Account":
        st.text_input("Choose a Username", key="signup_username")
        st.text_input("Choose a Password", type="password", key="signup_password")

        if st.button("Create Account"):
            username = st.session_state.signup_username.strip()
            password = st.session_state.signup_password
            if not username or not password:
                st.warning("⚠️ Please fill in all fields.")
            elif user_exists(username):
                st.error("🚫 Username already exists. Try another one.")
            else:
                created = create_user(username, password)
                if created:
                    st.success("✅ Account created successfully! You can now log in.")
                else:
                    st.error("❌ Failed to create account.")

    st.stop()

# =========================
# 💸 SPLITLAH APP BEGINS
# =========================
st.set_page_config(page_title="SplitLah", page_icon="💸")

# Floating animation
st.markdown(
    """
    <style>
    .floating-money {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        pointer-events: none; overflow: hidden; z-index: 0;
    }
    .floating-money span {
        position: absolute; font-size: 2.5rem; opacity: 0.3;
        animation: floatAround 18s ease-in-out infinite;
    }
    @keyframes floatAround {
        0%   { transform: translate(0, 0) rotate(0deg); opacity: 0.3; }
        25%  { transform: translate(40px, -60px) rotate(20deg); opacity: 0.5; }
        50%  { transform: translate(-50px, -120px) rotate(-15deg); opacity: 0.4; }
        75%  { transform: translate(30px, -40px) rotate(10deg); opacity: 0.6; }
        100% { transform: translate(0, 0) rotate(0deg); opacity: 0.3; }
    }
    </style>
    <div class="floating-money">
        <span style="top:5%;left:10%;animation-delay:0s;">💲</span>
        <span style="top:15%;left:80%;animation-delay:2s;">💵</span>
        <span style="top:30%;left:25%;animation-delay:4s;">💲</span>
        <span style="top:45%;left:60%;animation-delay:6s;">💵</span>
        <span style="top:55%;left:35%;animation-delay:8s;">💲</span>
        <span style="top:65%;left:75%;animation-delay:10s;">💵</span>
        <span style="top:75%;left:15%;animation-delay:12s;">💲</span>
        <span style="top:85%;left:50%;animation-delay:14s;">💵</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# Logo
logo_path = os.path.join(BASE_DIR, "splitlahlogo.png")
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)

# Load user groups into session (if not already loaded)
current_user = st.session_state.user_name
ud = get_user(current_user)
if ud:
    st.session_state.groups = ud.get("groups", {})
    # also ensure plan stored
    st.session_state.plan_type = ud.get("plan_type", st.session_state.plan_type)
    st.session_state.plan_duration = ud.get("plan_duration", st.session_state.plan_duration)
else:
    st.session_state.groups = {}

# helper to persist current session groups to user's JSON
def save_current_groups():
    update_user_groups(st.session_state.user_name, st.session_state.groups)

# --- Helper: Select or Create Group ---
def select_group():
    use_saved = st.radio("Select group option:", ["Create new group", "Use saved group"], key="group_option")
    if use_saved == "Use saved group":
        if st.session_state.get("groups"):
            selected = st.selectbox("Choose a group:", list(st.session_state["groups"].keys()), key="saved_group_select")
            members = st.session_state["groups"][selected]
        else:
            st.warning("No saved groups found. Please create one first.")
            members = []
    else:
        num_people = int(st.number_input("Number of people:", min_value=1, step=1, key="num_people_input"))
        members = [st.text_input(f"Enter name for person {i+1}:", key=f"person_{i}") for i in range(num_people)]
    st.session_state["current_members"] = members
    return members


# --- Helpers: Splits ---
def split_by_percentage(total, members, key_prefix="percent"):
    percentages = []
    for i, name in enumerate(members):
        key = f"{key_prefix}_{i}_{name}_pct"
        val = st.number_input(f"{name}'s share (%)", min_value=0.0, max_value=100.0, step=0.01, key=key)
        percentages.append(float(val))
    total_percent = sum(percentages)
    if abs(total_percent - 100) > 0.01:
        st.warning(f"⚠️ Total = {total_percent:.2f}% (must equal 100%)")
        return None
    return {name: (pct / 100) * total for name, pct in zip(members, percentages)}


def split_by_money(total, members, key_prefix="money"):
    amounts = []
    for i, name in enumerate(members):
        key = f"{key_prefix}_{i}_{name}_amt"
        val = st.number_input(f"{name}'s amount ($)", min_value=0.0, step=0.01, key=key)
        amounts.append(float(val))
    total_entered = sum(amounts)
    if total_entered == 0:
        st.info("Enter each person's contribution.")
        return None
    elif abs(total_entered - total) < 0.01:
        st.success("✅ Perfect! Total matches the bill.")
        return dict(zip(members, amounts))
    elif total_entered > total:
        st.error(f"⚠️ Total entered ({total_entered:.2f}) exceeds the bill ({total:.2f}).")
    else:
        st.warning(f"⚠️ Total entered ({total_entered:.2f}) is below the bill ({total:.2f}).")
    return None

# --- Live Exchange Rates ---
@st.cache_data(ttl=3600)
def get_live_rates():
    url = "https://open.er-api.com/v6/latest/USD"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "rates" in data:
            return data["rates"]
    except Exception:
        return {"USD":1.0,"EUR":0.91,"JPY":148.5,"MYR":4.6,"INR":83.5,"SGD":1.35}

rates = get_live_rates()
all_currencies = sorted(rates.keys())

# --- Currency Name Mapping ---
try:
    import pycountry
    currency_country_map = {c.alpha_3: c.name for c in pycountry.currencies}
except ImportError:
    currency_country_map = {
        "USD":"United States", "EUR":"Eurozone", "JPY":"Japan", "MYR":"Malaysia",
        "INR":"India", "SGD":"Singapore", "GBP":"United Kingdom", "AUD":"Australia",
        "CAD":"Canada", "CHF":"Switzerland", "CNY":"China", "HKD":"Hong Kong"
    }

def format_currency(c):
    return f"{c} ({currency_country_map.get(c,'Unknown')})"

# -----------------------
# PAGE FLOW (home / plan / main)
# -----------------------
if st.session_state.page == "plan_selection":
    st.title("Welcome to SplitLah 💸")
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    st.write(
        """
    **SplitLah** helps you split bills smartly and fairly.
    👉 Track spending, manage groups, and handle currency conversions with ease.
    Choose your plan to get started!
    """
    )
    st.header("💼 Choose Your Plan")
    plan = st.radio("Available Plans:", ["Basic", "Premium"], horizontal=True)
    st.markdown("---")
    if plan == "Basic":
        st.info("✅ Basic Plan:\n- Price: Free\n- Functions:\n  1. Create Groups\n  2. Normal Split")
        st.session_state.plan_type = "Basic"
    else:
        st.success(
            "🌟 Premium Plan:\n\n"
            "- Solo: \$2.99/month or \$29.90/year\n"
            "- Duo: \$4.98/month or \$49.80/year\n"
            "- Family: \$12.99/month or \$129.90/year\n"
            "- Business: \$24.99/month or \$249.90/year\n\n"
            "Features:\n1. Create Groups\n2. Normal Split\n3. Split within Budget\n4. Split + Currency"
        )
        tier = st.selectbox("Choose Premium Tier:", ["Solo", "Duo", "Family", "Business"])
        duration = st.radio("Billing cycle:", ["Monthly", "Yearly"], horizontal=True)
        st.session_state.plan_type = f"Premium {tier}"
        st.session_state.plan_duration = duration

    if st.button("🚀 Continue to App"):
        # persist plan to user record
        update_user_plan(st.session_state.user_name, st.session_state.plan_type, st.session_state.plan_duration)
        st.session_state.page = "main"
        st.rerun()
    if st.button("🚪 Log Out"):
        st.session_state.logged_in = False
        st.session_state.user_name = ""
        st.session_state.page = "plan_selection"
        st.success("✅ You have logged out successfully.")
        st.rerun()

elif st.session_state.page == "main":
    plan_type = st.session_state.plan_type
    duration = st.session_state.plan_duration

 # 👋 Welcome message above the plan
    if "user_name" in st.session_state and st.session_state.user_name:
        st.sidebar.markdown(f"### 👋 Welcome {st.session_state.user_name}!")
    if plan_type.startswith("Basic"):
        st.sidebar.markdown(f"**Current Plan:** {plan_type}")  
    elif plan_type.startswith("Premium"):
        st.sidebar.markdown(f"**Current Plan:** {plan_type} ({duration})")


    menu_options = ["🏠 Home", "1️⃣ Create Groups", "2️⃣ Normal Split"]
    if plan_type.startswith("Premium"):
        menu_options += ["3️⃣ Split within Budget", "4️⃣ Split + Currency"]

    menu = st.sidebar.radio("📋 Main Menu", menu_options)
        
# Home
    if menu == "🏠 Home":
        st.header("🏠 SplitLah Home")

        if plan_type.startswith("Basic"):
            st.write(f"Welcome, **{current_user}**! You are on the **{plan_type}** plan.")
            st.markdown("Navigate the functions using the sidebar\n" "\nAvailable Features:\n  1. Create Groups\n  2. Normal Split\n ")
            
        else:
            st.write(f"Welcome, **{current_user}**! You are on the **{plan_type}** ({duration}).")
            st.markdown("Navigate the function using the sidebar\n" "\nPremium Features:\n  1. Create Groups\n  2. Normal Split\n3. Split within Budget\n4. Split + Currency\n ")
        

        st.markdown("---")
        if st.button("🔄 Change Plan"):
            st.session_state.page = "plan_selection"
            st.rerun()

    # Create/Manage Groups
    elif menu == "1️⃣ Create Groups":
        st.header("👥 Create and Manage Groups")
        groups = st.session_state.get("groups", {})
        max_groups = 5 if plan_type.startswith("Basic") else float("inf")

        new_group = st.text_input("Enter group name:")
        num_members = int(st.number_input("Number of members:", min_value=1, step=1))
        if new_group:
            members = [st.text_input(f"Member {i+1} name:", key=f"{new_group}_m_{i}") for i in range(num_members)]
            if st.button("💾 Save Group"):
                valid = [m for m in members if m]
                if valid:
                    if len(groups) >= max_groups and new_group not in groups:
                        st.warning("🚫 Group limit reached for Basic plan.")
                    else:
                        groups[new_group] = valid
                        st.session_state.groups = groups
                        save_current_groups()
                        st.success(f"✅ Saved group '{new_group}'.")
                else:
                    st.warning("Enter at least one name.")

        if groups:
            st.subheader("📁 Saved Groups")
            for g, m in list(groups.items()):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{g}** → {', '.join(m)}")
                with col2:
                    new_name = st.text_input(f"Rename {g}", value=g, key=f"rename_{g}")
                    if st.button("✏️ Rename", key=f"btn_r_{g}"):
                        tgt = new_name.strip()
                        if not tgt:
                            st.warning("New name cannot be empty.")
                        elif tgt in groups and tgt != g:
                            st.error("A group with that name already exists.")
                        else:
                            groups[tgt] = groups.pop(g)
                            st.session_state.groups = groups
                            save_current_groups()
                            st.success(f"Renamed '{g}' → '{tgt}'.")
                            st.rerun()
                with col3:
                    if st.button("🗑️ Delete", key=f"del_{g}"):
                        groups.pop(g, None)
                        st.session_state.groups = groups
                        save_current_groups()
                        st.warning(f"Deleted '{g}'.")
                        st.rerun()

    # Normal Split
    elif menu == "2️⃣ Normal Split":
        st.header("💰 Normal Bill Split")
        members = select_group()
        if members:
            total = float(st.number_input("Enter total bill amount:", min_value=0.0, step=0.01))
            option = st.radio("Choose how to split:", ["Evenly", "By Percentage", "By Money"])
            if total > 0:
                if option == "Evenly":
                    each = total / len(members)
                    for name in members:
                        st.write(f"💵 {name} pays: **${each:.2f}**")
                elif option == "By Percentage":
                    results = split_by_percentage(total, members)
                    if results:
                        for n, a in results.items():
                            st.write(f"{n} → ${a:.2f}")
                elif option == "By Money":
                    results = split_by_money(total, members)
                    if results:
                        for n, a in results.items():
                            st.write(f"{n} → ${a:.2f}")

    # --- Split within Budget ---
    elif menu == "3️⃣ Split within Budget" and plan_type.startswith("Premium"):
        import uuid
        if "run_id" not in st.session_state:
            st.session_state.run_id = str(uuid.uuid4())[:8]

        def split_by_percentage(total, members, key_prefix="percent", calculate=False):
            unique_prefix = f"{key_prefix}_{st.session_state.run_id}"
            if not calculate:
                total_percentage = 0
                for i, name in enumerate(members):
                    key = f"{unique_prefix}_{i}_{name}_pct"
                    val = st.number_input(
                        f"{name}'s share (%)",
                        min_value=0.0,
                        max_value=100.0,
                        step=0.1,
                        key=key,
                    )
                    total_percentage += val
                st.write(f"Total entered: **{total_percentage:.1f}%** **(Must be 100%)**")
            else:
                total_percentage = sum(
                    st.session_state.get(f"{unique_prefix}_{i}_{name}_pct", 0)
                    for i, name in enumerate(members)
                )
                if abs(total_percentage - 100) > 0.01:
                    st.warning("⚠️ Percentages must total **100%**.")
                else:
                    st.subheader("💰 Split Results (By Percentage)")
                    for i, name in enumerate(members):
                        pct = st.session_state.get(f"{unique_prefix}_{i}_{name}_pct", 0)
                        amount = total * (pct / 100)
                        st.write(f"**{name}** pays: **${amount:.2f}**")

        def split_by_money(total, members, key_prefix="money", calculate=False):
            unique_prefix = f"{key_prefix}_{st.session_state.run_id}"
            if not calculate:
                for i, name in enumerate(members):
                    key = f"{unique_prefix}_{i}_{name}_amt"
                    st.number_input(
                        f"{name}'s contribution ($)",
                        min_value=0.0,
                        step=0.01,
                        key=key,
                    )
            else:
                total_entered = sum(
                    st.session_state.get(f"{unique_prefix}_{i}_{name}_amt", 0)
                    for i, name in enumerate(members)
                )
                if abs(total_entered - total) > 0.01:
                    st.warning(
                        f"⚠️ The total entered (${total_entered:.2f}) does not match the spend amount (${total:.2f})."
                    )
                else:
                    st.subheader("💰 Split Results (By Money)")
                    for i, name in enumerate(members):
                        amt = st.session_state.get(f"{unique_prefix}_{i}_{name}_amt", 0)
                        st.write(f"**{name}** pays: **${amt:.2f}**")

        st.header("📊 Split within a Budget")
        members = select_group()
        if members:
            if not st.session_state.loop_active:
                budget = st.number_input(
                    "Enter your total budget ($):",
                    min_value=0.00,
                    step=0.01,
                    value=max(0.00, st.session_state.budget_remaining) if st.session_state.budget_remaining != 0 else 0.00
                )
                if st.session_state.budget_remaining == 0 or st.session_state.budget_set != budget:
                    st.session_state.budget_remaining = budget
                    st.session_state.budget_set = budget

        st.write(f"💡 Remaining budget: **${st.session_state.budget_remaining:.2f}**")
        spend_amount = st.number_input("Enter amount to spend now ($):", min_value=0.00, step=0.01)
        option = st.radio("Choose how to split:", ["Evenly", "By Percentage", "By Money"])

    # --- Show input fields immediately ---
        if option == "By Percentage":
            split_by_percentage(spend_amount, members, key_prefix="budget", calculate=False)
        elif option == "By Money":
            split_by_money(spend_amount, members, key_prefix="budget_money", calculate=False)

    # --- Perform split when button pressed ---
        if st.button("✅ Split This Amount"):
            if spend_amount <= 0:
                st.warning("Please enter an amount greater than 0.")
            else:
                if option == "Evenly":
                    each = spend_amount / len(members)
                    for name in members:
                        st.write(f"{name} pays: **${each:.2f}**")

                elif option == "By Percentage":
                    split_by_percentage(spend_amount, members, key_prefix="budget", calculate=True)

                elif option == "By Money":
                    split_by_money(spend_amount, members, key_prefix="budget_money", calculate=True)

            st.session_state.budget_remaining -= spend_amount

            if st.session_state.budget_remaining > 0:
                st.success(f"✅ You still have ${st.session_state.budget_remaining:.2f} remaining.")
                st.session_state.loop_active = True
            elif st.session_state.budget_remaining == 0:
                st.info("💸 You’ve used your entire budget!")
                st.session_state.loop_active = False
            else:
                st.warning(f"⚠️ You have overspent by ${abs(st.session_state.budget_remaining):.2f}!")
                st.session_state.loop_active = False

    # --- Continue / End Session buttons ---
        if st.session_state.loop_active:
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➡️ Continue Spending"):
                    st.rerun()
            with col2:
                if st.button("🚪 End Session"):
                    st.session_state.loop_active = False 
                    st.session_state.budget_remaining = 0
                    st.session_state.budget_set = 0
                    st.success("✅ Budget session ended and reset.")
                    st.rerun()

    # --- Reset Budget button ---
        if st.button("🔄 Reset Budget"):
            st.session_state.budget_remaining = 0
            st.session_state.budget_set = 0
            st.session_state.loop_active = False
            st.session_state.run_id = str(uuid.uuid4())[:8]  # reset unique keys
            st.success("🔄 Budget has been reset.")

    # --- Split + Currency Conversion (Premium) ---
    elif menu=="4️⃣ Split + Currency" and plan_type.startswith("Premium"):
        st.header("💱 Split + Currency Conversion")
        members = select_group()
        if members:
            from_code = st.selectbox("From Currency", all_currencies, index=all_currencies.index("USD") if "USD" in all_currencies else 0, format_func=format_currency)
            to_code = st.selectbox("To Currency", all_currencies, index=all_currencies.index("USD") if "USD" in all_currencies else 0, format_func=format_currency)
            total = st.number_input(f"Enter total bill amount ({from_code}):", min_value=0.0, step=0.01)
            option = st.radio("Choose how to split:", ["Evenly","By Percentage","By Money"])
            if total>0:
                converted_total = total / rates[from_code] * rates[to_code]
                st.info(f"💱 1 {from_code} = {rates[to_code]/rates[from_code]:.4f} {to_code}")
                st.success(f"💰 Converted total: {converted_total:.2f} {to_code}")
                if option=="Evenly":
                    each = converted_total/len(members)
                    for name in members:
                        st.write(f"{name} pays: **{each:.2f} {to_code}**")
                elif option=="By Percentage":
                    results = split_by_percentage(converted_total, members)
                    if results:
                        for n, a in results.items():
                            st.write(f"{n} → {a:.2f} {to_code}")
                elif option=="By Money":
                    results = split_by_money(converted_total, members)
                    if results:
                        for n, a in results.items():
                            st.write(f"{n} → {a:.2f} {to_code}")
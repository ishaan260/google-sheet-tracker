import streamlit as st
import subprocess
import time

st.set_page_config(page_title="Dream Tracker", page_icon="💭", layout="centered")

st.title("💭 Dream Tracker App")
st.markdown("Run your Google Sheets + Playwright tracker easily from your browser.")

if st.button("▶ Run Tracker Script"):
    st.write("🚀 Running the tracker... Please wait.")
    progress = st.progress(0)

    # Run dream.py (your actual tracker script)
    process = subprocess.Popen(
        ["python", "dream.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Simulate progress
    for i in range(100):
        time.sleep(0.05)
        progress.progress(i + 1)

    out, err = process.communicate()

    if process.returncode == 0:
        st.success("✅ Tracker run complete!")
    else:
        st.error("❌ Error running tracker.")
        st.code(err)

    st.text_area("📜 Logs", out, height=300)
else:
    st.info("Click the button above to start the tracker.")
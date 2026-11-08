from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_all_pages_render_real_data_and_state_filter():
    app = AppTest.from_file(str(ROOT/"app.py"), default_timeout=45).run()
    assert not app.exception
    assert app.metric[1].label == "Delivered orders"
    full_count = int(app.metric[1].value.replace(",", ""))
    assert full_count == 96211
    assert app.metric[0].value == "R$ 13,181,027"
    app.multiselect[0].set_value(["SP"]).run()
    assert not app.exception
    assert int(app.metric[1].value.replace(",", "")) < full_count
    app.radio[0].set_value("Products & customers").run()
    assert not app.exception
    assert app.metric[0].label == "Purchasing customers"
    app.text_input[0].set_value("health").run()
    assert not app.exception
    assert all("health" in value for value in app.dataframe[0].value["category"])
    app.radio[0].set_value("Delivery & experience").run()
    assert not app.exception
    assert app.metric[0].label == "Late delivery rate"
    app.radio[0].set_value("Insights & methodology").run()
    assert not app.exception
    assert "Definitions you can audit" in [node.value for node in app.subheader]

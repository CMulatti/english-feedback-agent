"""
Tests de la interfaz con AppTest de Streamlit: ejecuta app.py sin abrir el navegador
y permite elegir opciones y presionar botones desde el código. Usa el LLM falso.
"""

from streamlit.testing.v1 import AppTest

from agent.tools import evaluar_texto as modulo_evaluar
from agent.tools import generar_retroalimentacion as modulo_generar
from config.settings import BASE_DIR
from tests.fakes import LLMFalso

RETRO = ("¡Muy bien! Usaste vocabulario de la clase, como mess hall. Para mejorar: Escribiste: "
         "'I go to bed'. Mejor: 'I go to bed at 10 pm'. Consejo: revisa tu texto antes de entregarlo.")


def abrir_app():
    app = AppTest.from_file(str(BASE_DIR / "app.py"), default_timeout=30)
    app.run()
    return app


def elegir_demo(app, escena):
    app.selectbox(key="demo").set_value(escena).run()


def test_la_app_abre_sin_errores():
    app = abrir_app()
    assert not app.exception
    assert app.title[0].value == "A2 Writing Assessment Agent"


def test_codigo_invalido_desactiva_evaluar():
    app = abrir_app()
    app.text_input(key="cadete_id").set_value("juan").run()
    app.text_area(key="texto").set_value("Hello Jim").run()
    assert app.button[0].disabled


def test_texto_en_espanol_se_deriva():
    app = abrir_app()
    elegir_demo(app, "4. Escalation: not in English")
    app.button[0].click().run()
    assert not app.exception
    assert "escalar_profesor" in app.error[0].value


def test_evaluar_ajustar_y_confirmar(monkeypatch):
    respuesta = "## Justification\nOK\n\nScores: Content 4 | Organization 4 | Language 3.5"
    monkeypatch.setattr(modulo_evaluar, "crear_llm", lambda: LLMFalso([respuesta] * 3))
    monkeypatch.setattr(modulo_generar, "crear_llm", lambda **k: LLMFalso([RETRO]))

    app = abrir_app()
    elegir_demo(app, "1. Standard case")
    app.button[0].click().run()
    assert app.number_input(key="puntaje_Content").value == 4

    # Ajuste sin razón: no se guarda
    app.number_input(key="puntaje_Language").set_value(3.0).run()
    confirmar = [b for b in app.button if b.label == "Confirm"][0]
    confirmar.click().run()
    assert "falta la razón" in app.error[0].value

    # Con razón: se guarda y aparece la retroalimentación
    app.text_input(key="razon_Language").set_value("Frequent article errors").run()
    [b for b in app.button if b.label == "Confirm"][0].click().run()
    assert "Assessment saved" in app.success[-1].value
    assert app.text_area[-1].value == RETRO


def test_pregunta_sugerida_en_el_chat(monkeypatch):
    from langchain_core.messages import AIMessage
    from agent import chat
    from tests.fakes import ChatFalsoConTools
    monkeypatch.setattr(chat, "crear_llm",
                        lambda: ChatFalsoConTools(messages=iter([AIMessage(content="It expects a reply to Jim.")])))
    app = abrir_app()
    sugerencia = [b for b in app.button if b.label.startswith("What does the")][0]
    sugerencia.click().run()
    assert not app.exception
    assert "It expects a reply to Jim." in [m.markdown[0].value for m in app.chat_message]


def test_cambiar_de_texto_borra_la_propuesta():
    app = abrir_app()
    elegir_demo(app, "4. Escalation: not in English")
    app.button[0].click().run()
    assert len(app.error) == 1                       # propuesta visible
    elegir_demo(app, "1. Standard case")
    assert len(app.error) == 0                       # al cargar otro texto, desaparece


def test_editar_el_texto_borra_la_propuesta():
    app = abrir_app()
    elegir_demo(app, "4. Escalation: not in English")
    app.button[0].click().run()
    app.text_area(key="texto").set_value("Hello Jim, I wake up at 6.").run()
    assert len(app.error) == 0
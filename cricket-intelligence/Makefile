install:
	pip install -r requirements.txt

run:
	uvicorn api:app --reload --port 8000

demo:
	python -c "from graph.graph import demo; import asyncio; asyncio.run(demo())"

trace:
	python -m webbrowser https://smith.langchain.com

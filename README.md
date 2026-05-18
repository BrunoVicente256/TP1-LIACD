## Pipeline

```bash
pip install -r requirements.txt
ollama pull llama3.1:8b
python src/visualizacao.py --input data/zones.json --output output/topologia_loja.png
python src/stitcher.py --input data/events.csv --output output/journeys.csv
python src/analytics.py --input output/journeys.csv --output output/metrics.json
python src/insights.py --input output/metrics.json --output output/insights.json
python src/report.py --metrics output/metrics.json --insights output/insights.json --output output/weekly_report.md

python evaluate.py --data events_validation.csv --output evaluation_report.json
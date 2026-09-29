def test_analytics_ranking(client):
    response = client.get("/api/v1/analytics/gastos?periodo=2024&top=10")
    assert response.status_code == 200

def test_search_operadoras(client):
    response = client.get("/api/v1/operadoras?q=amil&page=1&limit=10")
    assert response.status_code == 200

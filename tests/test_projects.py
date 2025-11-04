def test_create_and_list_projects(client, db, user):
    # create
    payload = {"name": "P1", "description": "demo"}
    r = client.post("/projects", json=payload)
    assert r.status_code == 200 or r.status_code == 201
    pid = r.json()["id"]

    # get by id
    r2 = client.get(f"/projects/{pid}")
    assert r2.status_code == 200
    assert r2.json()["name"] == "P1"

    # list
    r3 = client.get("/projects")
    assert r3.status_code == 200
    body = r3.json()
    assert any(p["id"] == pid for p in body)

    # update
    r4 = client.put(f"/projects/{pid}", json={"name": "P1-upd"})
    assert r4.status_code == 200
    assert r4.json()["name"] == "P1-upd"

import io


def test_upload_list_download_delete_document(client, db, user, s3_env):
    # create project
    r = client.post("/projects", json={"name": "Files", "description": ""})
    assert r.status_code in (200, 201)
    pid = r.json()["id"]

    # upload
    files = [("files", ("demo.txt", io.BytesIO(b"hello world"), "text/plain"))]
    r2 = client.post(f"/projects/{pid}/documents", files=files)
    assert r2.status_code == 201
    doc_id = r2.json()["files"][0]["id"]

    # list docs
    r3 = client.get(f"/projects/{pid}/documents")
    assert r3.status_code == 200
    assert any(d["id"] == doc_id for d in r3.json())

    # download
    r4 = client.get(f"/projects/document/{doc_id}")
    assert r4.status_code == 200
    assert r4.content == b"hello world"

    # update content
    files2 = {"file": ("demo.txt", io.BytesIO(b"changed"), "text/plain")}
    r5 = client.put(f"/projects/document/{doc_id}", files=files2)
    assert r5.status_code == 200

    r6 = client.get(f"/projects/document/{doc_id}")
    assert r6.status_code == 200
    assert r6.content == b"changed"

    # rename
    r7 = client.put(f"/projects/document/{doc_id}", data={"new_name": "renamed.txt"})
    assert r7.status_code == 200

    # delete
    r8 = client.delete(f"/projects/document/{doc_id}")
    assert r8.status_code in (200, 204)

    # ensure empty
    r9 = client.get(f"/projects/{pid}/documents")
    assert r9.status_code == 200
    assert r9.json() == []

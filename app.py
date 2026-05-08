# CIS2368 Homework 2
# Work Assignment System API
# Includes Extra Credit PUT /assignment

from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
CORS(app)

# database connection
def get_db_connection():
    return mysql.connector.connect(
        host="cis2368spring.cwxzkbq9zbfc.us-east-1.rds.amazonaws.com",
        user="admin",
        password="Netflix123",
        database="cis2368springdb"
    )

# home route
@app.route("/")
def home():
    return "Homework 2 API is running"


# POST /person - Add person
@app.route("/person", methods=["POST"])
def add_person():
    data = request.get_json()

    firstname = data.get("firstname")
    lastname = data.get("lastname")

    connection = get_db_connection()
    cursor = connection.cursor()

    query = "INSERT INTO person (firstname, lastname) VALUES (%s, %s)"
    cursor.execute(query, (firstname, lastname))
    connection.commit()

    cursor.close()
    connection.close()

    return jsonify({"message": "Person added successfully"})


# POST /job - Add job
@app.route("/job", methods=["POST"])
def add_job():
    data = request.get_json()
    # validate input
    if not data or not data.get("description") or not data.get("startdate") or not data.get("enddate"):
        return jsonify({"error": "All job fields are required"}), 400
    description = data.get("description")
    startdate = data.get("startdate")
    enddate = data.get("enddate")

    connection = get_db_connection()
    cursor = connection.cursor()

    query = "INSERT INTO job (description, startdate, enddate) VALUES (%s, %s, %s)"
    cursor.execute(query, (description, startdate, enddate))
    connection.commit()

    cursor.close()
    connection.close()

    return jsonify({"message": "Job added successfully"})


# POST /assignment - Add assignment (no overlapping jobs)
@app.route("/assignment", methods=["POST"])
def add_assignment():
    data = request.get_json()

    person_id = data.get("person_id")
    job_id = data.get("job_id")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # get job dates
    cursor.execute("SELECT startdate, enddate FROM job WHERE id = %s", (job_id,))
    job = cursor.fetchone()

    if not job:
        return jsonify({"error": "Job not found"}), 404

    startdate = job["startdate"]
    enddate = job["enddate"]

    # check overlap
    overlap_query = """
        SELECT j.startdate, j.enddate
        FROM assignment a
        JOIN job j ON a.job_id = j.id
        WHERE a.person_id = %s
        AND (
            (%s BETWEEN j.startdate AND j.enddate)
            OR
            (%s BETWEEN j.startdate AND j.enddate)
        )
    """

    cursor.execute(overlap_query, (person_id, startdate, enddate))
    conflict = cursor.fetchone()

    if conflict:
        cursor.close()
        connection.close()
        return jsonify({"error": "Person already assigned to overlapping job"}), 400

    insert_query = "INSERT INTO assignment (person_id, job_id, completed) VALUES (%s, %s, %s)"
    cursor.execute(insert_query, (person_id, job_id, False))
    connection.commit()

    cursor.close()
    connection.close()

    return jsonify({"message": "Assignment created successfully"})


# GET /jobs - Get a list of jobs and who is assigned to them
@app.route("/jobs", methods=["GET"])
def get_jobs():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT j.id, j.description, j.startdate, j.enddate,
               p.firstname, p.lastname
        FROM job j
        LEFT JOIN assignment a ON j.id = a.job_id
        LEFT JOIN person p ON a.person_id = p.id
    """

    cursor.execute(query)
    jobs = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(jobs)


# DELETE /job - Delete a job
@app.route("/job/<int:job_id>", methods=["DELETE"])
def delete_job(job_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    # delete related assignments first
    cursor.execute("DELETE FROM assignment WHERE job_id = %s", (job_id,))

    # delete job
    cursor.execute("DELETE FROM job WHERE id = %s", (job_id,))
    connection.commit()

    cursor.close()
    connection.close()

    return jsonify({"message": "Job deleted successfully"})


# PUT /assignment - Reassign a job to a new person (no overlap violation)
@app.route("/assignment/<int:job_id>", methods=["PUT"])
def update_assignment(job_id):
    data = request.get_json()
    new_person_id = data.get("person_id")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # get job dates
    cursor.execute("SELECT startdate, enddate FROM job WHERE id = %s", (job_id,))
    job = cursor.fetchone()

    if not job:
        return jsonify({"error": "Job not found"}), 404

    startdate = job["startdate"]
    enddate = job["enddate"]

    # check overlap for new person
    overlap_query = """
        SELECT j.startdate, j.enddate
        FROM assignment a
        JOIN job j ON a.job_id = j.id
        WHERE a.person_id = %s
        AND (
            (%s BETWEEN j.startdate AND j.enddate)
            OR
            (%s BETWEEN j.startdate AND j.enddate)
        )
    """

    cursor.execute(overlap_query, (new_person_id, startdate, enddate))
    conflict = cursor.fetchone()

    if conflict:
        cursor.close()
        connection.close()
        return jsonify({"error": "New person has overlapping job"}), 400

    cursor.execute("UPDATE assignment SET person_id = %s WHERE job_id = %s",
                   (new_person_id, job_id))
    connection.commit()

    cursor.close()
    connection.close()

    return jsonify({"message": "Assignment updated successfully"})


if __name__ == "__main__":
    app.run(debug=True)
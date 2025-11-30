from flask import Flask,render_template,request,session,redirect,url_for
import sqlite3
app=Flask(__name__)
app.secret_key = "abc-hospital"
def get_conn():
    conn=sqlite3.connect("project.db")
    conn.row_factory=sqlite3.Row
    return conn
@app.route("/", methods=["GET"])
def home():
    role = request.args.get("role")
    return render_template("home.html", role=role)

@app.route("/login", methods=["POST"])
def login():
    role = request.form.get("role")
    if role == "admin":
        user_id = request.form.get("user_id")
        password = request.form.get("password")
        if user_id == "1" and password == "admin123":
            session["role"] = "admin"
            return redirect(url_for("admin_dashboard"))
        else:
            return "Invalid Admin credentials", 401

    elif role == "doctor":
        id= request.form.get("doctor_id") 
        password = request.form.get("password")
        conn = get_conn()
        doctor = conn.execute("""SELECT d.doctor_id, d.name FROM Doctors d JOIN Users u ON d.user_id = u.user_id WHERE d.doctor_id= ? AND u.password= ? """, (id, password)).fetchone()
        conn.close()
        if doctor:
            session["doctor_id"] = doctor["doctor_id"]
            session["role"] = "doctor"  
            return redirect(url_for("doctor_dashboard"))
        else:
            return "Invalid Doctor credentials", 401

    elif role == "patient":
        id= request.form.get("user_id")
        password = request.form.get("password")
        conn = get_conn()
        patient = conn.execute("""
        SELECT p.patient_id, u.user_id
        FROM Patients p
        JOIN Users u ON p.user_id = u.user_id
        WHERE u.user_id=? AND u.password=?
        """, (id, password)).fetchone()
        conn.close()
        if patient:
            session["user_id"] = patient["user_id"] 
            session["role"] = "patient"
            return redirect(url_for("patient_dashboard"))
        else:
            return "Invalid Patient credentials", 401
        
@app.route("/admin")
def  admin_dashboard():
    conn = sqlite3.connect("project.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Doctors")
    total_doctors = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Patients")
    total_patients = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Appointments")
    total_appointments = cursor.fetchone()[0]
    cursor.execute("SELECT count(*) FROM Treatments")
    total_treatments=cursor.fetchone()[0]
    conn.close()

    return render_template("admin_dashboard.html",
                           total_doctors=total_doctors,
                           total_patients=total_patients,
                           total_appointments=total_appointments,
                           total_treatments=total_treatments)
@app.route("/doctor_dashboard")
def doctor_dashboard():
    doctor_id = session.get("doctor_id")
    conn = sqlite3.connect("project.db")
    total_patients = conn.execute("""
        SELECT COUNT(*) 
        FROM Patients 
        WHERE doctor_id = ?
    """, (doctor_id,)).fetchone()[0]
    total_appointments = conn.execute("""
        SELECT COUNT(*) 
        FROM Appointments 
        WHERE doctor_id = ?
    """, (doctor_id,)).fetchone()[0]
    total_treatments = conn.execute("""
    SELECT COUNT(*)
    FROM Treatments t
    JOIN Appointments a ON t.appointment_id = a.appointment_id
    WHERE a.doctor_id = ?
""", (doctor_id,)).fetchone()[0]
    conn.close()
    return render_template("doctor_dashboard.html",
                           total_patients=total_patients,
                           total_appointments=total_appointments,
                           total_treatments=total_treatments)
@app.route("/patient_dashboard")
def patient_dashboard():
    user_id = session.get("user_id")
    conn = get_conn()
    patients = conn.execute("SELECT * FROM Patients WHERE user_id=?", (user_id,)).fetchone()
    if patients is None:
        conn.close()
        return "Patient record not found", 404
    id = patients["patient_id"]
    appointments = conn.execute("""
        SELECT appointment_id, patient_id, doctor_id, date, time, status
        FROM Appointments
        WHERE patient_id=?
    """, (id,)).fetchall()
    treatments = conn.execute("""
        SELECT t.treatment_id, t.appointment_id, t.diagnosis, t.prescription, t.notes
        FROM Treatments t
        JOIN Appointments a ON t.appointment_id = a.appointment_id
        WHERE a.patient_id=?
    """, (id,)).fetchall()
    total_appointments = conn.execute(
        "SELECT COUNT(*) FROM Appointments WHERE patient_id=?",
        (id,)
    ).fetchone()[0]
    total_treatments = conn.execute("""SELECT COUNT(*) FROM Treatments t JOIN Appointments a ON t.appointment_id = a.appointment_id WHERE a.patient_id = ?""",(id,)).fetchone()[0]
    conn.close()
    return render_template(
        "patient_profile.html",
        patients=patients,
        treatments=treatments,
        appointments=appointments,
        total_appointments=total_appointments,
        total_treatments=total_treatments,
    )
@app.route("/patient")
def patient_list():
    conn = get_conn()
    role = session.get("role")

    if role == "doctor":
        doctor_id = session.get("doctor_id")
        patients = conn.execute("""
            SELECT patient_id, user_id, name, age, doctor_id, gender, email, address, phone_num
            FROM Patients
            WHERE doctor_id = ?
        """, (doctor_id,)).fetchall()

    elif role=="patient":
        user_id = session.get("user_id")
        patient = conn.execute("SELECT * FROM Patients WHERE user_id=?", (user_id,)).fetchone()
        if patient:
            patient_id = patient["patient_id"]
            appointments = conn.execute("""
                SELECT appointment_id, doctor_id, date, time, status
                FROM Appointments
                WHERE patient_id=?
            """, (patient_id,)).fetchall()

            treatments = conn.execute("""
                SELECT t.treatment_id, t.appointment_id, t.diagnosis, t.prescription, t.notes
                FROM Treatments t
                JOIN Appointments a ON t.appointment_id = a.appointment_id
                WHERE a.patient_id=?
            """, (patient_id,)).fetchall()
            total_appointments = len(appointments)
            total_treatments = len(treatments)
            conn.close()
            return render_template("patient_profile.html",
                                   patient=patient,
                                   total_appointments=total_appointments,
                                   total_treatments=total_treatments,
                                   appointments=appointments,
                                   treatments=treatments)

    else:
        patients = conn.execute("""
            SELECT patient_id, user_id, name, age, doctor_id, gender, email, address, phone_num
            FROM Patients
        """).fetchall()

    conn.close()
    return render_template("patient_dashboard.html", patients=patients)

@app.route("/patient/add",methods=["GET","POST"])
def add_patient():
    if request.method=="POST":
        data=(request.form["patient_id"],
              request.form["user_id"],
              request.form["name"],
              request.form["age"],
              request.form["doctor_id"],
              request.form["gender"],
              request.form["email"],
              request.form["address"],
              request.form["phone_num"]
              )
        conn=get_conn()
        conn.execute("insert into Patients(patient_id,user_id,name,age,doctor_id,gender,email,address,phone_num) values(?,?,?,?,?,?,?,?,?)",data)
        conn.commit()
        conn.close()
        return redirect(url_for("patient_list"))
    return render_template("add_patient.html")
@app.route("/patient/edit/<int:patient_id>",methods=["GET","POST"])
def edit_patient(patient_id):
    conn=get_conn()
    patient=conn.execute("select * from Patients where patient_id=?",(patient_id,)).fetchone()
    if request.method=="POST":
        update_data=(request.form["user_id"],
                     request.form["name"],
                     request.form["age"],
                     request.form["doctor_id"],
                     request.form["gender"],
                     request.form["email"],
                     request.form["phone_num"],
                     request.form["address"],patient_id
                     )
        conn.execute("update Patients set user_id=?,name=?,age=?,doctor_id=?,gender=?,email=?,phone_num=?,address=? where patient_id=?",update_data)
        conn.commit()
        conn.close()
        return redirect(url_for('patient_list'))
    conn.close()
    return render_template("edit_patient.html",patient=patient)
@app.route("/delete/patient/<int:patient_id>",methods=["POST","GET"])
def delete_patient(patient_id):
    conn=get_conn()
    conn.execute("delete from Patients where patient_id=?",(patient_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('patient_list'))
@app.route("/appointment")
@app.route("/appointment")
def appointment_list():
    conn = get_conn()
    role = session.get("role")

    if role == "doctor":
        doctor_id = session.get("doctor_id")
        appointments = conn.execute("""
            SELECT appointment_id, patient_id, doctor_id, date, time, status
            FROM Appointments
            WHERE doctor_id = ?
        """, (doctor_id,)).fetchall()

    elif role == "patient":
        user_id = session.get("user_id")
        patient = conn.execute("SELECT * FROM Patients WHERE user_id=?", (user_id,)).fetchone()
        if patient:
            patient_id = patient["patient_id"]
            appointments = conn.execute("""
                SELECT appointment_id, patient_id, doctor_id, date, time, status
                FROM Appointments
                WHERE patient_id = ?
            """, (patient_id,)).fetchall()
        else:
            appointments = []

    else:
        appointments = conn.execute("""
            SELECT appointment_id, patient_id, doctor_id, date, time, status
            FROM Appointments
        """).fetchall()

    conn.close()
    return render_template("appointment_dashboard.html", appointments=appointments)
@app.route("/appointment/add",methods=["GET","POST"])
def add_appointment():
    if request.method=="POST":
        data=(
            request.form["appointment_id"],
            request.form["patient_id"],
            request.form["doctor_id"],
            request.form["date"],
            request.form["time"],
            request.form["status"]
        )
        conn=get_conn()
        conn.execute("insert into Appointments values(?,?,?,?,?,?)",data)
        conn.commit()
        conn.close()
        return redirect(url_for('appointment_list'))
    return render_template("add_appointment.html")
@app.route("/appointment/edit/<int:appointment_id>",methods=["GET","POST"])
def edit_appointment(appointment_id):
    conn=get_conn()
    appointment=conn.execute("select * from Appointments where appointment_id=?",(appointment_id,)).fetchone()
    if request.method=="POST":
        update_data=(request.form["appointment_id"],
                     request.form["doctor_id"],
                    request.form["patient_id"],
                    request.form["date"],
                    request.form["time"],
                    request.form["status"],appointment_id
                    )
        conn.execute("update Appointments set appointment_id=?,doctor_id=?,patient_id=?,date=?,time=?,status=? where appointment_id=?",update_data)
        conn.commit()
        conn.close()
        return redirect(url_for('appointment_list'))
    conn.close()
    return render_template("edit_appointment.html",appointment=appointment)
@app.route("/appointment/delete/<int:appointment_id>",methods=["POST"])
def delete_appointment(appointment_id):
    conn=get_conn()
    conn.execute("delete from Appointments where appointment_id=?",(appointment_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("appointment_list"))
    

@app.route("/doctor")
def doctors_list():
    conn=get_conn()
    doctors=conn.execute('select * from Doctors').fetchall()
    conn.close()
    return render_template("doctor.html",doctors=doctors)
@app.route("/doctor/add", methods=["GET", "POST"])
def add_doctor():
    if request.method == "POST":
        data=(
            request.form["doctor_id"],
            request.form["user_id"],
            request.form["name"],
            request.form["specialization"],
            request.form["email"],
            request.form["availability"],
            request.form["status"]
        )
        conn = get_conn()
        conn.execute("""
            INSERT INTO Doctors (doctor_id,user_id, name, specialization, email, availability, status)
            VALUES (?,?, ?, ?, ?, ?, ?)
        """, data)
        conn.commit()
        conn.close()
        return redirect(url_for("doctors_list"))
    return render_template("add_doctor.html")
@app.route("/doctor/edit/<int:doctor_id>",methods=["GET","POST"])
def edit_doctor(doctor_id):
    conn=get_conn()
    doctor=conn.execute("select * from Doctors where doctor_id=?",(doctor_id,))
    if request.method=="POST":

        update_doctor=(
        request.form["name"],
        request.form["specialization"],
        request.form["email"],
        request.form["availability"],
        request.form["status"],doctor_id)
        conn.execute("UPDATE doctors set name=?,specialization=?,email=?,availability=?,status=? where doctor_id=?",update_doctor)
        conn.commit()
        conn.close()
        return redirect(url_for("doctors_list"))
    conn.close()
    return render_template("edit_doctor.html",doctor=doctor)
@app.route("/doctor/delete/<int:doctor_id>",methods=["POST"])
def delete_doctor(doctor_id):
    conn=get_conn()
    conn.execute("delete from doctors where doctor_id=?",(doctor_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("doctors_list"))
@app.route("/treatments")
def treatment_list():
    conn = get_conn()
    role = session.get("role")

    if role == "doctor":
        doctor_id = session.get("doctor_id")
        treatments = conn.execute("""
            SELECT t.treatment_id, t.appointment_id, t.diagnosis, t.prescription, t.notes
            FROM Treatments t
            JOIN Appointments a ON t.appointment_id = a.appointment_id
            WHERE a.doctor_id = ?
        """, (doctor_id,)).fetchall()

    elif role == "patient":
        user_id = session.get("user_id")
        patient = conn.execute("SELECT * FROM Patients WHERE user_id=?", (user_id,)).fetchone()
        if patient:
            patient_id = patient["patient_id"]
            treatments = conn.execute("""
                SELECT t.treatment_id, t.appointment_id, t.diagnosis, t.prescription, t.notes
                FROM Treatments t
                JOIN Appointments a ON t.appointment_id = a.appointment_id
                WHERE a.patient_id = ?
            """, (patient_id,)).fetchall()
        else:
            treatments = []

    else:
        treatments = conn.execute("""
            SELECT t.treatment_id, t.appointment_id, t.diagnosis, t.prescription, t.notes
            FROM Treatments t
            JOIN Appointments a ON t.appointment_id = a.appointment_id
        """).fetchall()

    conn.close()
    return render_template("treatment.html", treatments=treatments)

@app.route("/treatment/add", methods=["GET", "POST"])
def add_treatment():
    if request.method == "POST":
        data=(
            request.form["treatment_id"],
            request.form["appointment_id"],
            request.form["diagnosis"],
            request.form["prescription"],
            request.form["notes"]
        )
        conn = get_conn()
        conn.execute("""
            INSERT INTO Treatments (treatment_id,appointment_id, diagnosis, prescription, notes)
            VALUES (?,?, ?, ?, ?)
        """, data)
        conn.commit()
        conn.close()
        return redirect(url_for("treatment_list"))
    return render_template("add_treatment.html")
@app.route("/treatment/edit/<int:treatment_id>",methods=["GET","POST"])
def edit_treatment(treatment_id):
    conn=get_conn()
    treatment=conn.execute("select * from Treatments where treatment_id=?",(treatment_id,)).fetchone()
    if request.method=="POST":
        update_treatment=(
        request.form["appointment_id"],
        request.form["diagnosis"],
        request.form["prescription"],
        request.form["notes"],treatment_id)
        conn.execute("UPDATE Treatments set appointment_id=?,diagnosis=?,prescription=?,notes=? where treatment_id=?",update_treatment)
        conn.commit()
        conn.close()
        return redirect(url_for("treatment_list"))
    conn.close()
    return render_template("edit_treatment.html",treatment=treatment)
@app.route("/treatment/delete/<int:treatment_id>",methods=["POST"])
def delete_treatment(treatment_id):
    conn=get_conn()
    conn.execute("delete from Treatments where treatment_id=?",(treatment_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("treatment_list"))
if __name__=="__main__":
    app.run(debug=True)

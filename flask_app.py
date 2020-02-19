import os
import time
from datetime import datetime
os.environ["TZ"] =  'Asia/Kolkata'
time.tzset()


from flask import session, render_template, g
from flask import Flask, flash, request, redirect, url_for, send_file, Response
from werkzeug.utils import secure_filename
from werkzeug.wsgi import FileWrapper
from io import BytesIO

from flask_mysqldb import MySQL

import ibm_boto3
from ibm_botocore.client import Config, ClientError
import math


# Constants for IBM COS values
COS_ENDPOINT = "xx" # Current list avaiable at https://control.cloud-object-storage.cloud.ibm.com/v2/endpoints
COS_API_KEY_ID = "xx" # eg "W00YiRnLW4a3fTjMB-oiB-2ySfTrFBIQQWanc--P3byk"
COS_AUTH_ENDPOINT = "xx"
COS_RESOURCE_CRN = "xx" # eg "crn:v1:bluemix:public:cloud-object-storage:global:a/3bf0d9003abfb5d29761c3e97696b71c:d6f04d83-6c4f-4a62-a165-696756d63903::"

app = Flask(__name__)



app = Flask(__name__)
app.config['MYSQL_HOST'] = 'xx'
app.config['MYSQL_USER'] = 'xx'
app.config['MYSQL_PASSWORD'] = 'xx'
app.config['MYSQL_DB'] = 'xx'
mysql = MySQL(app)
app.secret_key = os.urandom(24)


ALLOWED_EXTENSIONS = set(['zip'])

#cred = (('298115', 'probhakar', 'Msil@123', 'all'),)
# defining users based on id for restricting usage
#all_user = ['298115']
#ibm = [999999]
'''file_exist = ((1,'Suzuki_Connect_Android_1.0.6.zip', '1.0.6','Test Server', 'Minal','android','pending','pending'),
              (2,'Suzuki_Connect_ios_1.6.zip', '1.6','Test Server', 'Ritika','iOS','NG','Probhakar'))'''

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
def index():
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        session.pop('user', None)
        cur.execute('SELECT * FROM username WHERE id = {};'.format(request.form['username']))
        userdata = cur.fetchall()
        print(userdata)
        if (len(userdata) > 0):
            if request.form['username'] in [userdata[0][0]]:
                if request.form['password'] in [userdata[0][2]]:
                    session['user'] = request.form['username']
                    # handling admin
                    if (userdata[0][3] == 'all'):
                        return redirect(url_for('sconnect_dashboard'))

                    # handling ibm
                    elif (userdata[0][3] =='sconnect'):
                        return redirect(url_for('sconnect_dashboard'))
                        print('ibm')

                    # handling harman
                    elif (userdata[0][3] == 'sps'):
                        return redirect(url_for('sconnect_dashboard'))
                        print('harman')

                    # handling mixlab
                    elif (userdata[0][3] == 'spd'):
                        return redirect(url_for('sconnect_dashboard'))
                        print('mix')
                    else:
                        return show_notification('', 'You are hacker!')
    return render_template('index.html')

@app.route('/sconnectdashboard',methods=['GET', 'POST'])
def sconnect_dashboard():
    cur = mysql.connection.cursor()
    #global file_exist
    global COS_ENDPOINT

    if request.method == 'POST':
        #print('request received')
        # check if the post request has the file part
        try:
            cur.execute("SELECT sr,pkname,version,server_type,uploaded_by,os,state,state_by,msil_comment,date_time FROM sconnect ORDER BY sr DESC")
            file_exist = cur.fetchall()
            aNG=0
            aGG=0
            iNG=0
            iGG=0
            for each in file_exist:
                if each[5] == 'android':
                    if each[6] == 'GG':
                        aGG += 1
                    elif each[6] == 'NG':
                        aNG +=1
                elif each[5] == 'iOS':
                    if each[6] == 'GG':
                        iGG += 1
                    elif each[6] == 'NG':
                        iNG +=1

        except Exception as e:
                return show_notification('/sconnectdashboard', e.message)

        if request.form['btn'] == 'Upload' and g.user:
            if 'file' not in request.files:
                flash('No file part')
                return show_notification('/sconnectdashboard', "oops, No file part")

            file = request.files['file']

            file.seek(0, os.SEEK_END)
            size = file.tell()
            # seek to its beginning, so you might save it entirely
            file.seek(0)
            # if user does not select file, browser also
            # submit an empty part without filename
            if file.filename == '':
                flash('No selected file')
                return show_notification('/sconnectdashboard', "oops, No file selected!")
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                #print(filename, [temp[1] for temp in file_exist])
                if filename in [temp[1] for temp in file_exist]:
                    return show_notification('/sconnectdashboard', "oops, file name already exists!")
                elif request.form['version'] in [temp[2] for temp in file_exist]:
                    return show_notification('/sconnectdashboard', "oops, version already exists!")
                elif request.form['version'].strip() == '':
                    return show_notification('/sconnectdashboard', "oops, version should not be empty!")

                #file_exist = file_exist+ ((3, filename,request.form['version'], request.form['server'], session['user'],request.form['os'],'pending','pending'),)
                #for i in file_exist:
                #    print(i)
                else:
                    try:
                        #COS_ENDPOINT = 'https://' + 's3.jp-tok.cloud-object-storage.appdomain.cloud'
                        multi_part_upload_manual("suzukiconnect", filename, file, size)
                        try:
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            cur.execute("SELECT name FROM username WHERE id = '{}';".format(g.user))
                            name = cur.fetchall()[0][0]
                            #print(name)
                            cur.execute("INSERT INTO sconnect (pkname, date_time, uploaded_by, os, version, state, state_by, msil_comment,server_type) VALUES('{}','{}','{}','{}','{}','pending','pending','Package not checked yet!','{}');".format(filename,str(timestamp),name,request.form['os'],request.form['version'],request.form['server']))
                            mysql.connection.commit()
                            return show_notification('/sconnectdashboard', 'Upload successful!!')

                        except Exception as e:
                            print(e)
                            return show_notification('/sconnectdashboard', 'Upload unsuccessful!!<br>'+str(e))


                    except Exception as e:
                        #print(e)
                        return show_notification('/sconnectdashboard', 'Upload unsuccessful!!<br>'+str(e))
            return show_notification('/sconnectdashboard', 'oops, unsupported file format!')

        elif request.form['btn'] == 'Feedback' and g.user:
            #print(request.form['feedback'].splitlines())
            #print(request.form['pkname'])
            #return ('<script>alert("'+'\\n'.join(request.form['feedback'].splitlines())+'")</script>')
            #UPDATE sconnect SET state='NG', msil_comment='bad app', state_by='Probhakar' WHERE pkname='Sconnect_iOS_test_1_0_1_6.zip';
            try:
                cur.execute("SELECT name FROM username WHERE id = '{}';".format(g.user))
                name = cur.fetchall()[0][0]
                cur.execute("UPDATE sconnect SET state='{}', msil_comment='{}', state_by='{}' WHERE pkname='{}';".format(request.form['status'], request.form['feedback'], name, request.form['pkname']))
                mysql.connection.commit()
                return redirect(url_for('sconnect_dashboard'))
            except Exception as e:
                #print(e)
                return show_notification('/sconnectdashboard', 'Update unsuccessful!!<br>'+str(e))


        elif request.form['btn'] == 'Download' and g.user:
            #print(request.form)
            #print(request.form['pdkname'])
            #return (request.form['pdkname'])
            try:
                #fobj = get_item("suzukiconnect",request.form['pdkname'])
                #return send_file(fobj.read(), attachment_filename=request.form['pdkname'], as_attachment=True)
                #return show_notification('ok')
                try:
                    # create client object
                    cos = ibm_boto3.resource("s3",
                        ibm_api_key_id=COS_API_KEY_ID,
                        ibm_service_instance_id=COS_RESOURCE_CRN,
                        ibm_auth_endpoint=COS_AUTH_ENDPOINT,
                        config=Config(signature_version="oauth"),
                        endpoint_url=COS_ENDPOINT
                    )
                    file = cos.Object("suzukiconnect", request.form['pdkname']).get()
                    #file = cos.Bucket(bucket_name).Object('my-key')
                    #print(file)
                    #dd = file["Body"].read()
                    #print(type(dd))
                    print(file["Body"])
                    #print(len(file["Body"].read()))
                    #return send_file(dd, attachment_filename='sample.zip', as_attachment=True)
                    '''with open(item_name+'.zip', "wb") as file_data:
                        file_data.write(dd)
                    file_data.close()'''
                    #return send_file(file["Body"].read(), attachment_filename=item_name, as_attachment=True)
                    #fileobj = file["Body"]
                    #return fileobj
                    w = FileWrapper(BytesIO(file['Body'].read()))
                    #print('under w')
                    try:
                        return Response(w, mimetype="application/zip", direct_passthrough=True, headers={"Content-Disposition": "attachment;filename={}".format(request.form['pdkname'])})
                    except Exception as e:
                        print("upload excp: {0}".format(e))

                except ClientError as be:
                    print("CLIENT ERROR: {0}\n".format(be))
                except Exception as e:
                    print("Unable to retrieve file contents: {0}".format(e))
            except Exception as e:
                #print(e)
                return show_notification('/sconnectdashboard', 'Download unsuccessful!!<br>'+str(e))

            return show_notification('/sconnectdashboard', 'ok')
    else:
        if g.user:
            #cur = mysql.connection.cursor()

            cur.execute('SELECT responsiblefor FROM username WHERE id = {};'.format(g.user))
            permission = cur.fetchall()

            try:
                cur.execute("SELECT sr,pkname,version,server_type,uploaded_by,os,state,state_by,msil_comment,date_time FROM sconnect ORDER BY sr DESC")
                file_exist = cur.fetchall()
                aNG=0
                aGG=0
                iNG=0
                iGG=0
                for each in file_exist:
                    if each[5] == 'android':
                        if each[6] == 'GG':
                            aGG += 1
                        elif each[6] == 'NG':
                            aNG +=1
                    elif each[5] == 'iOS':
                        if each[6] == 'GG':
                            iGG += 1
                        elif each[6] == 'NG':
                            iNG +=1
            except Exception as e:
                    return show_notification('/sconnectdashboard', str(e))


            if (permission[0][0] == 'all'):
                #print(timestamp)
                #try:
                    #cur.execute("INSERT INTO sconnect (pkname, date_time, uploaded_by, os, version, state, state_by, msil_comment) VALUES('Suzuki_Connect_ios_1_6_1.zip','{}','Minal','iOS','1.6.1','NG','Probhakar','1.bad app\\n2.goodapp');".format(str(timestamp)))
                    #mysql.connection.commit()
                    #print(cur.fetchall())
                    #print(file_exist)
                #except Exception as e:
                    #print('unable to insert\\n',e.message)
                return render_template('dasboard_sconnect_admin.html', file_exist=file_exist, android=[aGG,aNG],apple=[iGG,iNG])

            elif(permission[0][0] == 'sconnect'):
                return render_template('dasboard_sconnect_ibm.html', file_exist=file_exist, android=[aGG,aNG],apple=[iGG,iNG])


            elif(permission[0][0] == 'sps'):
                #return render_template('dasboard_sconnect_ibm.html', file_exist=file_exist, android=[10,8],apple=[8,7])
                return redirect(url_for('sps_dashboard'))


            elif(permission[0][0] == 'spd'):
                #return render_template('dasboard_sconnect_ibm.html', file_exist=file_exist, android=[10,8],apple=[8,7])
                return redirect(url_for('spd_dashboard'))


            else:
                return show_notification('/sconnectdashboard', 'not admin')

        return redirect(url_for('index'))


# smartplaystudio -------------------------->>
@app.route('/spsdashboard',methods=['GET', 'POST'])
def sps_dashboard():
    cur = mysql.connection.cursor()
    #global file_exist
    global COS_ENDPOINT

    if request.method == 'POST':
        #print('request received')
        # check if the post request has the file part
        try:
            cur.execute("SELECT sr,pkname,version,server_type,uploaded_by,os,state,state_by,msil_comment,date_time FROM sps ORDER BY sr DESC")
            file_exist = cur.fetchall()
            aNG=0
            aGG=0
            iNG=0
            iGG=0
            for each in file_exist:
                if each[5] == 'android':
                    if each[6] == 'GG':
                        aGG += 1
                    elif each[6] == 'NG':
                        aNG +=1
                elif each[5] == 'iOS':
                    if each[6] == 'GG':
                        iGG += 1
                    elif each[6] == 'NG':
                        iNG +=1

        except Exception as e:
                return show_notification('/spsdashboard', e.message)

        if request.form['btn'] == 'Upload' and g.user:
            if 'file' not in request.files:
                flash('No file part')
                return show_notification('/spsdashboard', "oops, No file part")

            file = request.files['file']

            file.seek(0, os.SEEK_END)
            size = file.tell()
            # seek to its beginning, so you might save it entirely
            file.seek(0)
            # if user does not select file, browser also
            # submit an empty part without filename
            if file.filename == '':
                flash('No selected file')
                return show_notification('/spsdashboard', "oops, No file selected!")
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                #print(filename, [temp[1] for temp in file_exist])
                if filename in [temp[1] for temp in file_exist]:
                    return show_notification('/spsdashboard', "oops, file name already exists!")
                elif request.form['version'] in [temp[2] for temp in file_exist]:
                    return show_notification('/spsdashboard', "oops, version already exists!")
                elif request.form['version'].strip() == '':
                    return show_notification('/spsdashboard', "oops, version should not be empty!")

                #file_exist = file_exist+ ((3, filename,request.form['version'], request.form['server'], session['user'],request.form['os'],'pending','pending'),)
                #for i in file_exist:
                #    print(i)
                else:
                    try:
                        #COS_ENDPOINT = 'https://' + 's3.jp-tok.cloud-object-storage.appdomain.cloud'
                        multi_part_upload_manual("smartplaystudio", filename, file, size)
                        try:
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            cur.execute("SELECT name FROM username WHERE id = '{}';".format(g.user))
                            name = cur.fetchall()[0][0]
                            #print(name)
                            cur.execute("INSERT INTO sps (pkname, date_time, uploaded_by, os, version, state, state_by, msil_comment,server_type) VALUES('{}','{}','{}','{}','{}','pending','pending','Package not checked yet!','{}');".format(filename,str(timestamp),name,request.form['os'],request.form['version'],request.form['server']))
                            mysql.connection.commit()
                            return show_notification('/spsdashboard', 'Upload successful!!')

                        except Exception as e:
                            print(e)
                            return show_notification('/spsdashboard', 'Upload unsuccessful!!<br>'+str(e))


                    except Exception as e:
                        #print(e)
                        return show_notification('/spsdashboard', 'Upload unsuccessful!!<br>'+str(e))
            return show_notification('/spsdashboard', 'oops, unsupported file format!')

        elif request.form['btn'] == 'Feedback' and g.user:
            #print(request.form['feedback'].splitlines())
            #print(request.form['pkname'])
            #return ('<script>alert("'+'\\n'.join(request.form['feedback'].splitlines())+'")</script>')
            #UPDATE sconnect SET state='NG', msil_comment='bad app', state_by='Probhakar' WHERE pkname='Sconnect_iOS_test_1_0_1_6.zip';
            try:
                cur.execute("SELECT name FROM username WHERE id = '{}';".format(g.user))
                name = cur.fetchall()[0][0]
                cur.execute("UPDATE sps SET state='{}', msil_comment='{}', state_by='{}' WHERE pkname='{}';".format(request.form['status'], request.form['feedback'], name, request.form['pkname']))
                mysql.connection.commit()
                return redirect(url_for('sps_dashboard'))
            except Exception as e:
                #print(e)
                return show_notification('/spsdashboard', 'Update unsuccessful!!<br>'+str(e))


        elif request.form['btn'] == 'Download' and g.user:
            #print(request.form)
            #print(request.form['pdkname'])
            #return (request.form['pdkname'])
            try:
                #fobj = get_item("suzukiconnect",request.form['pdkname'])
                #return send_file(fobj.read(), attachment_filename=request.form['pdkname'], as_attachment=True)
                #return show_notification('ok')
                try:
                    # create client object
                    cos = ibm_boto3.resource("s3",
                        ibm_api_key_id=COS_API_KEY_ID,
                        ibm_service_instance_id=COS_RESOURCE_CRN,
                        ibm_auth_endpoint=COS_AUTH_ENDPOINT,
                        config=Config(signature_version="oauth"),
                        endpoint_url=COS_ENDPOINT
                    )
                    file = cos.Object("smartplaystudio", request.form['pdkname']).get()
                    #file = cos.Bucket(bucket_name).Object('my-key')
                    #print(file)
                    #dd = file["Body"].read()
                    #print(type(dd))
                    print(file["Body"])
                    #print(len(file["Body"].read()))
                    #return send_file(dd, attachment_filename='sample.zip', as_attachment=True)
                    '''with open(item_name+'.zip', "wb") as file_data:
                        file_data.write(dd)
                    file_data.close()'''
                    #return send_file(file["Body"].read(), attachment_filename=item_name, as_attachment=True)
                    #fileobj = file["Body"]
                    #return fileobj
                    w = FileWrapper(BytesIO(file['Body'].read()))
                    #print('under w')
                    try:
                        return Response(w, mimetype="application/zip", direct_passthrough=True, headers={"Content-Disposition": "attachment;filename={}".format(request.form['pdkname'])})
                    except Exception as e:
                        print("upload excp: {0}".format(e))

                except ClientError as be:
                    print("CLIENT ERROR: {0}\n".format(be))
                except Exception as e:
                    print("Unable to retrieve file contents: {0}".format(e))
            except Exception as e:
                #print(e)
                return show_notification('/spsdashboard', 'Download unsuccessful!!<br>'+str(e))

            return show_notification('/spsdashboard', 'ok')
    else:
        if g.user:
            #cur = mysql.connection.cursor()

            cur.execute('SELECT responsiblefor FROM username WHERE id = {};'.format(g.user))
            permission = cur.fetchall()

            try:
                cur.execute("SELECT sr,pkname,version,server_type,uploaded_by,os,state,state_by,msil_comment,date_time FROM sps ORDER BY sr DESC")
                file_exist = cur.fetchall()
                aNG=0
                aGG=0
                iNG=0
                iGG=0
                for each in file_exist:
                    if each[5] == 'android':
                        if each[6] == 'GG':
                            aGG += 1
                        elif each[6] == 'NG':
                            aNG +=1
                    elif each[5] == 'iOS':
                        if each[6] == 'GG':
                            iGG += 1
                        elif each[6] == 'NG':
                            iNG +=1
            except Exception as e:
                    return show_notification('/spsdashboard', str(e))


            if (permission[0][0] == 'all'):
                #print(timestamp)
                #try:
                    #cur.execute("INSERT INTO sconnect (pkname, date_time, uploaded_by, os, version, state, state_by, msil_comment) VALUES('Suzuki_Connect_ios_1_6_1.zip','{}','Minal','iOS','1.6.1','NG','Probhakar','1.bad app\\n2.goodapp');".format(str(timestamp)))
                    #mysql.connection.commit()
                    #print(cur.fetchall())
                    #print(file_exist)
                #except Exception as e:
                    #print('unable to insert\\n',e.message)
                return render_template('dashboard_smartplaystudio_admin.html', file_exist=file_exist, android=[aGG,aNG],apple=[iGG,iNG])

            elif(permission[0][0] == 'sconnect'):
                return redirect(url_for('index'))


            elif(permission[0][0] == 'sps'):
                #return render_template('dasboard_sconnect_ibm.html', file_exist=file_exist, android=[10,8],apple=[8,7])
                return render_template('dashboard_smartplaystudio_harman.html', file_exist=file_exist, android=[aGG,aNG],apple=[iGG,iNG])


            elif(permission[0][0] == 'spd'):
                #return render_template('dasboard_sconnect_ibm.html', file_exist=file_exist, android=[10,8],apple=[8,7])
                return redirect(url_for('index'))


            else:
                return show_notification('/spsdashboard', 'not admin')

        return redirect(url_for('index'))

# smartplaydock -------------------------->>
@app.route('/spddashboard',methods=['GET', 'POST'])
def spd_dashboard():
    cur = mysql.connection.cursor()
    #global file_exist
    global COS_ENDPOINT

    if request.method == 'POST':
        #print('request received')
        # check if the post request has the file part
        try:
            cur.execute("SELECT sr,pkname,version,server_type,uploaded_by,os,state,state_by,msil_comment,date_time FROM spd ORDER BY sr DESC")
            file_exist = cur.fetchall()
            aNG=0
            aGG=0
            iNG=0
            iGG=0
            for each in file_exist:
                if each[5] == 'android':
                    if each[6] == 'GG':
                        aGG += 1
                    elif each[6] == 'NG':
                        aNG +=1
                elif each[5] == 'iOS':
                    if each[6] == 'GG':
                        iGG += 1
                    elif each[6] == 'NG':
                        iNG +=1

        except Exception as e:
                return show_notification('/spddashboard', e.message)

        if request.form['btn'] == 'Upload' and g.user:
            if 'file' not in request.files:
                flash('No file part')
                return show_notification('/spddashboard', "oops, No file part")

            file = request.files['file']

            file.seek(0, os.SEEK_END)
            size = file.tell()
            # seek to its beginning, so you might save it entirely
            file.seek(0)
            # if user does not select file, browser also
            # submit an empty part without filename
            if file.filename == '':
                flash('No selected file')
                return show_notification('/spddashboard', "oops, No file selected!")
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                #print(filename, [temp[1] for temp in file_exist])
                if filename in [temp[1] for temp in file_exist]:
                    return show_notification('/spddashboard', "oops, file name already exists!")
                elif request.form['version'] in [temp[2] for temp in file_exist]:
                    return show_notification('/spddashboard', "oops, version already exists!")
                elif request.form['version'].strip() == '':
                    return show_notification('/spddashboard', "oops, version should not be empty!")

                #file_exist = file_exist+ ((3, filename,request.form['version'], request.form['server'], session['user'],request.form['os'],'pending','pending'),)
                #for i in file_exist:
                #    print(i)
                else:
                    try:
                        #COS_ENDPOINT = 'https://' + 's3.jp-tok.cloud-object-storage.appdomain.cloud'
                        multi_part_upload_manual("smartplaydock", filename, file, size)
                        try:
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            cur.execute("SELECT name FROM username WHERE id = '{}';".format(g.user))
                            name = cur.fetchall()[0][0]
                            #print(name)
                            cur.execute("INSERT INTO spd (pkname, date_time, uploaded_by, os, version, state, state_by, msil_comment,server_type) VALUES('{}','{}','{}','{}','{}','pending','pending','Package not checked yet!','{}');".format(filename,str(timestamp),name,request.form['os'],request.form['version'],request.form['server']))
                            mysql.connection.commit()
                            return show_notification('/spddashboard', 'Upload successful!!')

                        except Exception as e:
                            print(e)
                            return show_notification('/spddashboard', 'Upload unsuccessful!!<br>'+str(e))


                    except Exception as e:
                        #print(e)
                        return show_notification('/spddashboard', 'Upload unsuccessful!!<br>'+str(e))
            return show_notification('/spddashboard', 'oops, unsupported file format!')

        elif request.form['btn'] == 'Feedback' and g.user:
            #print(request.form['feedback'].splitlines())
            #print(request.form['pkname'])
            #return ('<script>alert("'+'\\n'.join(request.form['feedback'].splitlines())+'")</script>')
            #UPDATE sconnect SET state='NG', msil_comment='bad app', state_by='Probhakar' WHERE pkname='Sconnect_iOS_test_1_0_1_6.zip';
            try:
                cur.execute("SELECT name FROM username WHERE id = '{}';".format(g.user))
                name = cur.fetchall()[0][0]
                cur.execute("UPDATE spd SET state='{}', msil_comment='{}', state_by='{}' WHERE pkname='{}';".format(request.form['status'], request.form['feedback'], name, request.form['pkname']))
                mysql.connection.commit()
                return redirect(url_for('spd_dashboard'))
            except Exception as e:
                #print(e)
                return show_notification('/spddashboard', 'Update unsuccessful!!<br>'+str(e))


        elif request.form['btn'] == 'Download' and g.user:
            #print(request.form)
            #print(request.form['pdkname'])
            #return (request.form['pdkname'])
            try:
                #fobj = get_item("suzukiconnect",request.form['pdkname'])
                #return send_file(fobj.read(), attachment_filename=request.form['pdkname'], as_attachment=True)
                #return show_notification('ok')
                try:
                    # create client object
                    cos = ibm_boto3.resource("s3",
                        ibm_api_key_id=COS_API_KEY_ID,
                        ibm_service_instance_id=COS_RESOURCE_CRN,
                        ibm_auth_endpoint=COS_AUTH_ENDPOINT,
                        config=Config(signature_version="oauth"),
                        endpoint_url=COS_ENDPOINT
                    )
                    file = cos.Object("smartplaydock", request.form['pdkname']).get()
                    #file = cos.Bucket(bucket_name).Object('my-key')
                    #print(file)
                    #dd = file["Body"].read()
                    #print(type(dd))
                    print(file["Body"])
                    #print(len(file["Body"].read()))
                    #return send_file(dd, attachment_filename='sample.zip', as_attachment=True)
                    '''with open(item_name+'.zip', "wb") as file_data:
                        file_data.write(dd)
                    file_data.close()'''
                    #return send_file(file["Body"].read(), attachment_filename=item_name, as_attachment=True)
                    #fileobj = file["Body"]
                    #return fileobj
                    w = FileWrapper(BytesIO(file['Body'].read()))
                    #print('under w')
                    try:
                        return Response(w, mimetype="application/zip", direct_passthrough=True, headers={"Content-Disposition": "attachment;filename={}".format(request.form['pdkname'])})
                    except Exception as e:
                        print("upload excp: {0}".format(e))

                except ClientError as be:
                    print("CLIENT ERROR: {0}\n".format(be))
                except Exception as e:
                    print("Unable to retrieve file contents: {0}".format(e))
            except Exception as e:
                #print(e)
                return show_notification('/spddashboard', 'Download unsuccessful!!<br>'+str(e))

            return show_notification('/spddashboard', 'ok')
    else:
        if g.user:
            #cur = mysql.connection.cursor()

            cur.execute('SELECT responsiblefor FROM username WHERE id = {};'.format(g.user))
            permission = cur.fetchall()

            try:
                cur.execute("SELECT sr,pkname,version,server_type,uploaded_by,os,state,state_by,msil_comment,date_time FROM spd ORDER BY sr DESC")
                file_exist = cur.fetchall()
                aNG=0
                aGG=0
                iNG=0
                iGG=0
                for each in file_exist:
                    if each[5] == 'android':
                        if each[6] == 'GG':
                            aGG += 1
                        elif each[6] == 'NG':
                            aNG +=1
                    elif each[5] == 'iOS':
                        if each[6] == 'GG':
                            iGG += 1
                        elif each[6] == 'NG':
                            iNG +=1
            except Exception as e:
                    return show_notification('/spddashboard', str(e))


            if (permission[0][0] == 'all'):
                #print(timestamp)
                #try:
                    #cur.execute("INSERT INTO sconnect (pkname, date_time, uploaded_by, os, version, state, state_by, msil_comment) VALUES('Suzuki_Connect_ios_1_6_1.zip','{}','Minal','iOS','1.6.1','NG','Probhakar','1.bad app\\n2.goodapp');".format(str(timestamp)))
                    #mysql.connection.commit()
                    #print(cur.fetchall())
                    #print(file_exist)
                #except Exception as e:
                    #print('unable to insert\\n',e.message)
                return render_template('dashboard_smartplaydock_admin.html', file_exist=file_exist, android=[aGG,aNG],apple=[iGG,iNG])

            elif(permission[0][0] == 'sconnect'):
                return redirect(url_for('index'))


            elif(permission[0][0] == 'sps'):
                #return render_template('dasboard_sconnect_ibm.html', file_exist=file_exist, android=[10,8],apple=[8,7])
                return redirect(url_for('index'))


            elif(permission[0][0] == 'spd'):
                #return render_template('dasboard_sconnect_ibm.html', file_exist=file_exist, android=[10,8],apple=[8,7])
                return render_template('dashboard_smartplaydock_mixlab.html', file_exist=file_exist, android=[aGG,aNG],apple=[iGG,iNG])


            else:
                return show_notification('/spddashboard', 'not admin')

        return redirect(url_for('index'))




@app.route('/logout')
def dropsession():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/about')
def about():
    if g.user:
        return render_template('about.html')
    else:
        return redirect(url_for('index'))


@app.before_request
def before_request():
    g.user = None
    if 'user' in session:
        g.user = session['user']

def show_notification(where, message):
    ss = '''
            <!doctype html>
            <title>notification</title>
            <h1><a href="{}">{}<--Click to go back.</a></h1>
        '''
    return (ss.format(where, message))


# ibm file upload
def multi_part_upload_manual(bucket_name, item_name, file, length):
        try:
            # create client object
            cos_cli = ibm_boto3.client("s3",
                ibm_api_key_id=COS_API_KEY_ID,
                ibm_service_instance_id=COS_RESOURCE_CRN,
                ibm_auth_endpoint=COS_AUTH_ENDPOINT,
                config=Config(signature_version="oauth"),
                endpoint_url=COS_ENDPOINT
            )

            print("Starting multi-part upload for {0} to bucket: {1}\n".format(item_name, bucket_name))

            # initiate the multi-part upload
            mp = cos_cli.create_multipart_upload(
                Bucket=bucket_name,
                Key=item_name
            )

            upload_id = mp["UploadId"]

            # min 5MB part size
            part_size = 1024 * 1024 * 5
            file_size = length
            #print(file_size)
            part_count = int(math.ceil(file_size / float(part_size)))
            data_packs = []
            position = 0
            part_num = 0
            #ind = 0

            # begin uploading the parts
            #with open(file_path, "rb") as f:
            for i in range(part_count):
                part_num = i + 1
                part_size = min(part_size, (file_size - position))
                #print("partsize", part_size)

                print("Uploading to {0} (part {1} of {2})".format(item_name, part_num, part_count))

                file_data = file.read(part_size)
                #print(type(file_data))
                #print(len(file_data))

                mp_part = cos_cli.upload_part(
                    Bucket=bucket_name,
                    Key=item_name,
                    PartNumber=part_num,
                    Body=file_data,
                    ContentLength=part_size,
                    UploadId=upload_id
                )

                data_packs.append({
                    "ETag":mp_part["ETag"],
                    "PartNumber":part_num
                })

                position += part_size

            # complete upload
            cos_cli.complete_multipart_upload(
                Bucket=bucket_name,
                Key=item_name,
                UploadId=upload_id,
                MultipartUpload={
                    "Parts": data_packs
                }
            )
            print("Upload for {0} Complete!\n".format(item_name))
        except ClientError as be:
            # abort the upload
            cos_cli.abort_multipart_upload(
                Bucket=bucket_name,
                Key=item_name,
                UploadId=upload_id
            )
            print("Multi-part upload aborted for {0}\n".format(item_name))
            print("CLIENT ERROR: {0}\n".format(be))
        except Exception as e:
            print("Unable to complete multi-part upload: {0}".format(e))




if __name__ == '__main__':
    app.run(threaded=True)

## download iter
"""def get_item(bucket_name, item_name):
    print(bucket_name, item_name)
    global COS_ENDPOINT
    #COS_ENDPOINT = "https://s3.jp-tok.cloud-object-storage.appdomain.cloud"
    print("Retrieving item from bucket: {0}, key: {1}".format(bucket_name, item_name))
    try:
        # create client object
        cos = ibm_boto3.resource("s3",
            ibm_api_key_id=COS_API_KEY_ID,
            ibm_service_instance_id=COS_RESOURCE_CRN,
            ibm_auth_endpoint=COS_AUTH_ENDPOINT,
            config=Config(signature_version="oauth"),
            endpoint_url=COS_ENDPOINT
        )
        file = cos.Object(bucket_name, item_name).get()
        #file = cos.Bucket(bucket_name).Object('my-key')
        #print(file)
        #dd = file["Body"].read()
        #print(type(dd))
        print(file["Body"])
        #print(len(file["Body"].read()))
        #return send_file(dd, attachment_filename='sample.zip', as_attachment=True)
        '''with open(item_name+'.zip', "wb") as file_data:
            file_data.write(dd)
        file_data.close()'''
        #return send_file(file["Body"].read(), attachment_filename=item_name, as_attachment=True)
        #fileobj = file["Body"]
        #return fileobj
        w = FileWrapper(BytesIO(file['Body'].read()))
        print('under w')
        try:
            return Response(w, mimetype="application/zip", direct_passthrough=True)
        except Exception as e:
            print("upload excp: {0}".format(e))

    except ClientError as be:
        print("CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to retrieve file contents: {0}".format(e))"""







'''
@app.route('/getsession')
def getsession():
    if 'user' in session:
        return session['user']

    return 'Not logged in!'

@app.route('/dropsession')
def dropsession():
    session.pop('user', None)
    return 'Dropped!' '''



import os
from flask import Flask, render_template, request, jsonify, send_from_directory, session
from werkzeug.utils import secure_filename
from models import db, Template
import invoice_processing
import json
from json import dumps, loads
import datetime

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = './uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///templates.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/uploader')
def uploader():
    return render_template('index.html')

@app.route('/create_template', methods=['POST'])
def create_template():
    data = request.get_json()
    template_name = data['template_name']
    document_type = data['document_type']
    prompt_fields = data['prompt']

    if Template.query.filter_by(name=template_name.lower()).first():
        return jsonify(message='Template name already exists'), 400

    prompt_fields_with_category = [{"field": item["field"], "category": item["category"]} for item in prompt_fields]
    template = Template(name=template_name, document_type=document_type, prompt=json.dumps(prompt_fields), prompt_category=json.dumps(prompt_fields_with_category))
    db.session.add(template)
    db.session.commit()
    return jsonify(message='Template created successfully'), 201

@app.route('/modify_templates')
def modify_templates():
    return render_template('modify_template.html')

@app.route('/edit_template/<int:template_id>', methods=['GET'])
def edit_template(template_id):
    template = Template.query.get(template_id)
    if template is None:
        return "Template not found", 404

    try:
        prompt_fields = loads(template.prompt)
        prompt_categories = loads(template.prompt_category)
    except json.decoder.JSONDecodeError:
        prompt_fields = []

    return render_template(
        'edit_template.html',
        template_id=template.id,
        template_name=template.name,
        template_document_type=template.document_type,
        template_prompts=prompt_fields,
        template_prompt_categories=prompt_categories

    )
@app.route('/update_template/<int:template_id>', methods=['PUT'])
def update_template(template_id):
    data = request.get_json()
    template = Template.query.get(template_id)

    if template is None:
        return jsonify(message='Template not found'), 404

    template.name = data['template_name']
    template.document_type = data['document_type']
    prompt_fields_with_category = [{"field": item["field"], "category": item["category"]} for item in data['prompt']]
    template.prompt = json.dumps(data['prompt'])
    template.prompt_category = json.dumps(prompt_fields_with_category)

    db.session.commit()

    return jsonify(message='Template updated successfully'), 200

@app.route('/delete_template/<int:template_id>', methods=['DELETE'])
def delete_template(template_id):
    template = Template.query.get(template_id)
    if not template:
        return jsonify(message='Template not found'), 404

    db.session.delete(template)
    db.session.commit()

    return jsonify(message='Template deleted successfully'), 200

@app.route('/get_templates', methods=['GET'])
def get_templates():
    templates = Template.query.all()
    templates_list = [{'id': t.id, 'name': t.name, 'document_type': t.document_type, 'prompt': t.prompt} for t in templates]
    return jsonify(templates=templates_list), 200

@app.route('/process', methods=['POST'])
def process():
    try:
        # Perform invoice processing here and update the success variable accordingly
        success = True
    except Exception as e:
        success = False
        print("Error processing the file:", e)

    if success:
        return jsonify({'status': 'success', 'message': 'Processing completed successfully'})
    else:
        return jsonify({'status': 'error', 'message': 'An error occurred during processing'})

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify(message='No file part'), 400
    file = request.files['file']

    if file.filename == '':
        return jsonify(message='No file selected'), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    try:
        text = invoice_processing.extract_text_from_pdf(file_path)

        # Retrieve the template from the database
        template_id = request.form.get('template_id')
        template = Template.query.get(template_id)
        if template is None:
            return "Template not found", 404

        prompt_fields = json.loads(template.prompt)
        simple_fields = [field['field'] for field in prompt_fields if field['category'] == 'Simple Fields']
        column_fields = [field['field'] for field in prompt_fields if field['category'] == 'Column Fields']

        invoice_info, token_usage = invoice_processing.extract_invoice_information(text, simple_fields, column_fields)
        cost = token_usage * 0.002 / 1000
        print(f"Total tokens used: {token_usage}")
        print(f"Cost to process document: ${cost:.4f}")
        excel_filename = f"{os.path.splitext(filename)[0]}_invoice_info.xlsx"
        excel_filepath = os.path.join(app.config['UPLOAD_FOLDER'], excel_filename)
        invoice_processing.save_to_excel(excel_filepath, invoice_info, simple_fields, column_fields)

        return send_from_directory(app.config['UPLOAD_FOLDER'], excel_filename, as_attachment=True)
    except Exception as e:
        return "Error processing the file: " + str(e), 500

@app.route('/uploads/<filename>', methods=['GET'])
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
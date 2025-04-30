from flask import Flask, render_template, request, jsonify, session, send_file
import os
from datetime import datetime
import logging
import markdown2
from meta_agent import analyze_requirements

app = Flask(__name__)
app.secret_key = os.urandom(24)
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

os.makedirs('logs', exist_ok=True)

@app.route('/')
def home():
    session['conversation_id'] = datetime.now().strftime('%Y%m%d_%H%M%S')
    return render_template('index_req.html')

@app.route('/reason', methods=['POST'])
def reason():
    try:
        data = request.json
        requirements = data.get('requirements', [])
        threshold = float(data.get('threshold', 0.8))

        if not requirements or not isinstance(requirements, list):
            return jsonify({'error': 'Invalid or missing requirements'}), 400

        conversation_id = session.get('conversation_id', datetime.now().strftime('%Y%m%d_%H%M%S'))
        log_file = f"logs/conversation_{conversation_id}.md"

        result = analyze_requirements(requirements)

        # Save log
        with open(log_file, 'w') as f:
            f.write(f"# Requirements Analysis\n\n")
            f.write("\n".join(f"- {r}" for r in requirements) + "\n\n")
            f.write(f"## Satisfaction Score: {result['satisfaction']}\n\n")
            for category, issues in result['issues'].items():
                f.write(f"### {category.capitalize()}\n")
                for issue in issues:
                    f.write(f"- {issue}\n")
                f.write("\n")
            f.write("### Raw Output\n")
            f.write(result['raw_output'])

        with open(log_file, 'r') as f:
            html_content = markdown2.markdown(f.read())

        return jsonify({
            'issues': result['issues'],
            'satisfaction_level': result['satisfaction'],
            'satisfactory': result['satisfaction'] >= threshold,
            'log_content': html_content,
            'log_file': log_file
        })
    except Exception as e:
        logger.error(f"Error in reasoning: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download-log')
def download_log():
    file = request.args.get('file')
    if not file or not os.path.exists(file):
        return "File not found", 404
    return send_file(file, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5050)

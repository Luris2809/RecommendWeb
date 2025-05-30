from flask import Flask, render_template, request
from datetime import datetime, timedelta
import json
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static/images', exist_ok=True) # 例の画像を置くフォルダ

recommendations = [
    {
        'name': '素晴らしいコーヒーメーカー',
        'category': '家電',
        'likes': [],
        'historical_likes': {},
        'like_count': 0,
        'file_path': 'static/images/item1.jpg'
    },
    {
        'name': 'おしゃれなスニーカー',
        'category': 'ファッション',
        'likes': [],
        'historical_likes': {},
        'like_count': 0,
        'file_path': 'static/images/item2.png'
    },
    {
        'name': '感動的な風景動画',
        'category': 'エンタメ',
        'likes': [],
        'historical_likes': {},
        'like_count': 0,
        'file_path': 'static/images/item3.mp4'
    },
    {
        'name': '面白いGIFアニメ',
        'category': 'エンタメ',
        'likes': [],
        'historical_likes': {},
        'like_count': 0,
        'file_path': 'static/images/item4.gif'
    }
]
debug_year_offset = 0  # デバッグ用の年オフセット

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_likes_for_period(item, days=None):
    if days is None:
        return len(item.get('likes', []))
    else:
        cutoff = datetime.now() - timedelta(days=days)
        return sum(1 for like in item.get('likes', []) if like.get('timestamp') > cutoff)

def get_all_time_likes(item):
    all_likes = len(item.get('likes', []))
    historical_total = sum(count for count in item.get('historical_likes', {}).values())
    return all_likes + historical_total

@app.route('/')
def index():
    for item in recommendations:
        item['likes_last_30_days'] = calculate_likes_for_period(item, 30)
        item['likes_last_year'] = calculate_likes_for_period(item, 365)
        item['all_time_likes'] = get_all_time_likes(item)
    return render_template('form.html', recommendations=recommendations, error=None)

@app.route('/submit', methods=['POST'])
def handle_submission():
    item_name = request.form['item_name']
    category = request.form['category']
    file = request.files['file']
    filename = None

    if not item_name or not category:
        error_message = "商品名とカテゴリの両方を入力してください。"
        return render_template('form.html', recommendations=recommendations, error=error_message)

    if file:
        if not allowed_file(file.filename):
            error_message = "許可されていないファイル形式です。"
            return render_template('form.html', recommendations=recommendations, error=error_message)
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    for i, item in enumerate(recommendations):
        if item['name'] == item_name and item['category'] == category:
            error_message = f"「{item_name} ({category})」はすでに登録されています。"
            return render_template('form.html', recommendations=recommendations, error=error_message)

    recommendation = {'name': item_name, 'category': category, 'likes': [], 'historical_likes': {}, 'like_count': 0}
    if filename:
        recommendation['file_path'] = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    recommendations.append(recommendation)
    return render_template('form.html', recommendations=recommendations, error=None)

@app.route('/like/<item_name>/<category>')
def like_item(item_name, category):
    user_id = request.remote_addr
    for item in recommendations:
        if item['name'] == item_name and item['category'] == category:
            already_liked = any(like.get('user_id') == user_id for like in item.get('likes', []))
            if already_liked:
                return render_template('form.html', recommendations=recommendations, error="すでに「いいね！」済みです。")

            item['likes'].append({'timestamp': datetime.now(), 'user_id': user_id})
            item['like_count'] = len(item['likes'])
            break
    for item in recommendations:
        item['likes_last_30_days'] = calculate_likes_for_period(item, 30)
        item['likes_last_year'] = calculate_likes_for_period(item, 365)
        item['all_time_likes'] = get_all_time_likes(item)
    return render_template('form.html', recommendations=recommendations, error=None)

@app.route('/edit_submit', methods=['POST'])
def handle_edit_submission():
    original_item_name = request.form['original_item_name']
    original_category = request.form['original_category']
    edit_item_name = request.form['edit_item_name']
    edit_category = request.form['edit_category']
    file = request.files['edit_file']
    filename = None

    if not edit_item_name or not edit_category:
        error_message = "商品名とカテゴリの両方を入力してください。"
        return render_template('form.html', recommendations=recommendations, error=error_message)

    if file:
        if not allowed_file(file.filename):
            error_message = "許可されていないファイル形式です。"
            return render_template('form.html', recommendations=recommendations, error=error_message)
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    for i, item in enumerate(recommendations):
        if item['name'] == original_item_name and item['category'] == original_category:
            recommendations[i]['name'] = edit_item_name
            recommendations[i]['category'] = edit_category
            if filename:
                recommendations[i]['file_path'] = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            break

    return render_template('form.html', recommendations=recommendations, error=None, message="商品を編集しました。")

@app.route('/reset_likes_yearly')
def reset_likes():
    global debug_year_offset
    current_year = str(datetime.now().year + debug_year_offset)
    for item in recommendations:
        item['historical_likes'][current_year] = len(item.get('likes', []))
        item['likes'] = []
        item['like_count'] = 0
    debug_year_offset += 1
    for item in recommendations:
        item['likes_last_30_days'] = calculate_likes_for_period(item, 30)
        item['likes_last_year'] = calculate_likes_for_period(item, 365)
        item['all_time_likes'] = get_all_time_likes(item)
    return render_template('form.html', recommendations=recommendations, error=None, message="いいね！数を年間リセットしました。")

@app.route('/debug')
def debug():
    return render_template('debug.html', recommendations=recommendations)

if __name__ == '__main__':
    app.run(debug=True)
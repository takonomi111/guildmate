from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from models import db, Member, Tag, Game, Event, EventParticipant

app = Flask(__name__)
import os
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.secret_key = 'secret'
db.init_app(app)

with app.app_context():
    db.create_all()

@app.template_filter('highlight')
def highlight(text, keyword):
    if not keyword:
        return text
    return text.replace(keyword, f"<mark>{keyword}</mark>")

# ---------- メンバー管理 ----------

@app.route('/')
def index():
    keyword = request.args.get('q', '')
    tag_filter = request.args.get('tag', '')
    game_filter = request.args.get('game', '')
    sort_option = request.args.get('sort', 'name')
    favorite_only = request.args.get('favorite', '')

    query = Member.query

    if keyword:
        query = query.join(Member.tags, isouter=True).join(Member.games, isouter=True).filter(
            (Member.name.contains(keyword)) |
            (Member.note.contains(keyword)) |
            (Tag.name.contains(keyword)) |
            (Game.name.contains(keyword))
        ).distinct()

    if tag_filter:
        query = query.join(Member.tags).filter(Tag.name == tag_filter)

    if game_filter:
        query = query.join(Member.games).filter(Game.name == game_filter)

    if favorite_only == 'on':
        query = query.filter(Member.favorite == True)

    if sort_option == 'name':
        query = query.order_by(Member.favorite.desc(), Member.name.asc())
    elif sort_option == 'latest':
        query = query.order_by(Member.favorite.desc(), Member.id.desc())
    elif sort_option == 'oldest':
        query = query.order_by(Member.favorite.desc(), Member.id.asc())
    elif sort_option == 'favorite':
        query = query.order_by(Member.favorite.desc(), Member.name.asc())

    members = query.all()
    all_tags = Tag.query.order_by(Tag.name).all()
    all_games = Game.query.order_by(Game.name).all()

    return render_template("index.html", members=members,
                           all_tags=all_tags, all_games=all_games,
                           selected_tag=tag_filter, selected_game=game_filter,
                           selected_sort=sort_option, keyword=keyword,
                           favorite_only=favorite_only)

@app.route('/toggle_favorite/<int:member_id>', methods=['POST'])
def toggle_favorite(member_id):
    member = Member.query.get_or_404(member_id)
    member.favorite = not member.favorite
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    total_members = Member.query.count()
    tag_counts = {tag.name: len(tag.members) for tag in Tag.query.all()}
    game_counts = {game.name: len(game.members) for game in Game.query.all()}
    recent_members = Member.query.order_by(Member.id.desc()).limit(5).all()
    return render_template("dashboard.html", total=total_members,
                           tag_counts=tag_counts, game_counts=game_counts,
                           recent_members=recent_members)

@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    if request.method == 'POST':
        name = request.form['name']
        note = request.form['note']
        tag_names = [t.strip() for t in request.form['tags'].split(',') if t.strip()]
        game_names = [g.strip() for g in request.form['games'].split(',') if g.strip()]
        member = Member(name=name, note=note)

        for tag_name in tag_names:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            member.tags.append(tag)

        for game_name in game_names:
            game = Game.query.filter_by(name=game_name).first()
            if not game:
                game = Game(name=game_name)
                db.session.add(game)
            member.games.append(game)

        db.session.add(member)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template("add.html")

@app.route('/edit_member/<int:member_id>', methods=['GET', 'POST'])
def edit_member(member_id):
    member = Member.query.get_or_404(member_id)

    if request.method == 'POST':
        member.name = request.form['name']
        member.note = request.form['note']
        tag_names = [t.strip() for t in request.form['tags'].split(',') if t.strip()]
        game_names = [g.strip() for g in request.form['games'].split(',') if g.strip()]
        member.tags.clear()
        member.games.clear()

        for tag_name in tag_names:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            member.tags.append(tag)

        for game_name in game_names:
            game = Game.query.filter_by(name=game_name).first()
            if not game:
                game = Game(name=game_name)
                db.session.add(game)
            member.games.append(game)

        db.session.commit()
        return redirect(url_for('index'))

    tag_string = ', '.join(tag.name for tag in member.tags)
    game_string = ', '.join(game.name for game in member.games)
    return render_template("edit.html", member=member,
                           tag_string=tag_string, game_string=game_string)

@app.route('/delete_member/<int:member_id>', methods=['POST'])
def delete_member(member_id):
    member = Member.query.get_or_404(member_id)
    db.session.delete(member)
    db.session.commit()
    return redirect(url_for('index'))

# ---------- イベント管理 ----------

@app.route('/events')
def list_events():
    selected_game_id = request.args.get('game')
    games = Game.query.order_by(Game.name).all()
    if selected_game_id:
        events = Event.query.filter_by(game_id=selected_game_id).order_by(Event.date.asc()).all()
    else:
        events = Event.query.order_by(Event.date.asc()).all()
    return render_template("events.html", events=events, games=games, selected_game_id=selected_game_id)

@app.route('/events/new', methods=['GET', 'POST'])
def create_event():
    games = Game.query.order_by(Game.name).all()
    if request.method == 'POST':
        title = request.form['title']
        date_str = request.form['date']
        description = request.form['description']
        game_id = int(request.form['game'])
        date = datetime.strptime(date_str, "%Y-%m-%d").date()

        event = Event(title=title, date=date, description=description, game_id=game_id)
        member_ids = request.form.getlist('members')
        for member_id in member_ids:
            participant = EventParticipant(
                member_id=int(member_id),
                status=request.form.get(f"status_{member_id}", '未定')
            )
            event.participants.append(participant)

        db.session.add(event)
        db.session.commit()
        flash('イベントを作成しました。')
        return redirect(url_for('list_events'))

    selected_game_id = request.args.get('game')
    selected_game = Game.query.get(selected_game_id) if selected_game_id else None
    members = selected_game.members if selected_game else []

    return render_template("create_event.html", games=games, selected_game=selected_game, members=members)

@app.route('/events/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    participants = event.participants

    by_status = {
        "参加": [],
        "不参加": [],
        "未定": []
    }

    for participant in participants:
        by_status.get(participant.status, by_status["未定"]).append(participant.member)

    return render_template("event_detail.html", event=event, by_status=by_status)

@app.route('/events/<int:event_id>/edit', methods=['GET', 'POST'])
def edit_event_participation(event_id):
    event = Event.query.get_or_404(event_id)

    if request.method == 'POST':
        for participant in event.participants:
            new_status = request.form.get(f"status_{participant.member_id}", "未定")
            participant.status = new_status
        db.session.commit()
        flash('参加状況を更新しました')
        return redirect(url_for('event_detail', event_id=event.id))

    return render_template("edit_event_participation.html", event=event)

# ---------- カレンダー ----------

@app.route('/calendar')
def calendar_view():
    return render_template("calendar.html")

@app.route('/calendar/events')
def calendar_events():
    events = Event.query.all()
    event_list = []
    for event in events:
        event_list.append({
            "title": event.title,
            "start": event.date.isoformat(),
            "url": url_for("event_detail", event_id=event.id)
        })
    return jsonify(event_list)

# ----------------------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

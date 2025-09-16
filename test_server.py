#!/usr/bin/env python3
"""
Test web server that mimics the Kaktus website structure.
Used for testing bot notifications by changing HTML content.
"""

from flask import Flask, render_template, request, redirect, url_for, flash
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'test-secret-key-for-kaktus-testing'

# Store current event data
current_event = {
    'title': 'Dobíječka 20.9.2025 15:00 - 18:00',
    'description': 'Získej 50 Kč navíc při dobití 200 Kč! Akce platí pouze dnes.',
    'bonus_text': 'Bonus 50 Kč při dobití 200 Kč nebo více',
    'active': True
}

@app.route('/')
def index():
    """Main page mimicking Kaktus structure."""
    return render_template('kaktus_test.html', event=current_event)

@app.route('/admin')
def admin():
    """Admin page to edit the event content."""
    return render_template('admin.html', event=current_event)

@app.route('/admin/update', methods=['POST'])
def update_event():
    """Update the event content."""
    global current_event
    
    current_event['title'] = request.form['title']
    current_event['description'] = request.form['description'] 
    current_event['bonus_text'] = request.form['bonus_text']
    current_event['active'] = 'active' in request.form
    
    flash('Event updated successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/clear')
def clear_event():
    """Clear/disable current event."""
    global current_event
    current_event['active'] = False
    flash('Event cleared!', 'info')
    return redirect(url_for('admin'))

# Create templates directory if it doesn't exist
if not os.path.exists('templates'):
    os.makedirs('templates')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
# app.py - Interfaccia web
from flask import Flask, render_template, request, jsonify, redirect, flash
from main import ConsigliAsta
import os

app = Flask(__name__)
app.secret_key = 'fantacalcio_2026_secret_key'

consigli_engine = ConsigliAsta()

csv_path = 'data/giocatori.csv'
if os.path.exists(csv_path):
    consigli_engine.carica_da_csv(csv_path)
    print(f"✅ Caricato CSV da giocatori da {csv_path}")
else:
    print(f"⚠️ File {csv_path} non trovato!")
    if os.pathsep.exists('giocatori.csv'):
        consigli_engine.carica_da_csv('giocatori.csv')
        print("✅ Caricato CSV dalla root directory")

@app.route('/')
def index():
    stats = {
        'totale': len(consigli_engine.giocatori),
        'P': len([g for g in consigli_engine.giocatori if g.ruolo == 'P']),
        'D': len([g for g in consigli_engine.giocatori if g.ruolo == 'D']),
        'C': len([g for g in consigli_engine.giocatori if g.ruolo == 'C']),
        'A': len([g for g in consigli_engine.giocatori if g.ruolo == 'A']),
        'acquistati': len(consigli_engine.acquistati)
    }
    return render_template('index.html', stats=stats)

@app.route('/consigli', methods=['GET', 'POST'])
def consigli():
    if request.method == 'POST':
        ruolo = request.form.get('ruolo', 'tutti')
        budget = request.form.get('budget', type=float)
        top_n = request.form.get('top_n', 10, type=int)
        
        if budget is None:
            budget = consigli_engine.budget_rimasto
            
        suggerimenti = consigli_engine.suggerisci(
            ruolo=ruolo if ruolo != 'tutti' else None,
            budget=budget,
            escludi=consigli_engine.acquistati,
            top_n=top_n
        )
        
        return render_template('consigli.html', 
                             suggerimenti=suggerimenti,
                             ruolo=ruolo,
                             budget=budget,
                             acquistati=consigli_engine.acquistati)
    
    return render_template('consigli.html', 
                         suggerimenti=None,
                         acquistati=consigli_engine.acquistati)

@app.route('/strategia')
def strategia():
    budget_totale = request.args.get('budget', 500, type=float)
    posti = {'P': 3, 'D': 8, 'C': 8, 'A': 6}
    strategia = consigli_engine.strategia_asta(budget_totale, posti)
    return render_template('strategia.html', strategia=strategia, posti=posti)

@app.route('/acquista', methods=['POST'])
def acquista():
    nome = request.form.get('nome')
    if nome:
        consigli_engine.aggiorna_acquistato(nome)
    return jsonify({'success': True, 'acquistati': consigli_engine.acquistati})

@app.route('/rimuovi_acquistato', methods=['POST'])
def rimuovi_acquistato():
    global gestione_asta
    nome = request.form.get('nome')
    ruolo = request.form.get('ruolo')
    squadra = request.form.get('squadra')
    
    if nome and gestione_asta:
        risultato = gestione_asta.rimuovi_acquisto(nome, ruolo, squadra)
        flash(risultato.get('message', '✅ Rimosso!'), 'success' if risultato.get('success', True) else 'error')
        return redirect('/dashboard')
    
    flash('❌ Errore: giocatore non trovato', 'error')
    return redirect('/dashboard')

@app.route('/reset')
def reset():
    consigli_engine.resetta()
    return jsonify({'success': True, 'message': 'Lista resettata'})

# Dashboard asta
# Inizializza la gestione asta
gestione_asta = None

@app.route('/dashboard')
def dashboard():
    global gestione_asta
    if gestione_asta is None:
        gestione_asta = consigli_engine.init_gestione()
    
    # Aggiorna i consigli per la fase corrente
    consigli = gestione_asta.get_consigli_fase()
    stats = gestione_asta.get_statistiche()
    
    return render_template('dashboard.html',
                         stats=stats,
                         acquisti=gestione_asta.acquisti,
                         consigli=consigli)

@app.route('/acquista_asta', methods=['POST'])
def acquista_asta():
    global gestione_asta
    nome = request.form.get('nome')
    ruolo = request.form.get('ruolo')
    squadra = request.form.get('squadra')
    quotazione_base = float(request.form.get('quotazione_base', 0))
    prezzo_pagato = float(request.form.get('prezzo_pagato', quotazione_base))
    
    if nome and gestione_asta:
        risultato = gestione_asta.aggiungi_acquisto(
            nome=nome,
            ruolo=ruolo,
            squadra=squadra,
            costo=prezzo_pagato,
            quotazione_base=quotazione_base,
            automatico=False
        )
        # Usa flash invece dell'URL
        flash(risultato.get('message', '✅ Acquisto effettuato!'), 'success' if risultato.get('success', True) else 'error')
        return redirect('/dashboard')
    
    flash('❌ Errore: giocatore non valido', 'error')
    return redirect('/dashboard')

@app.route('/avanza_fase', methods=['POST'])
def avanza_fase():
    global gestione_asta
    if gestione_asta:
        gestione_asta.avanza_fase()
    return redirect('/dashboard')

@app.route('/listone')
def listone():
    # Prepara tutti i giocatori con il loro stato
    giocatori = []
    for g in consigli_engine.giocatori:
        stato = consigli_engine.get_stato_giocatore(g.nome)
        giocatori.append({
            'nome': g.nome,
            'ruolo': g.ruolo,
            'squadra': g.squadra,
            'quotazione': g.quotazione,
            'fantamedia': g.fantamedia,
            'gol': g.gol,
            'assist': g.assist,
            'indice': g.calcola_indice(),
            'stato': stato
        })
    
    # Ordina per indice decrescente
    giocatori.sort(key=lambda x: x['indice'], reverse=True)
    
    # Trova il miglior giocatore disponibile
    suggerimento_top = None
    for g in giocatori:
        if g['stato'] == 'disponibile':
            suggerimento_top = g
            break
    
    # Statistiche
    stats = {
        'totale': len(giocatori),
        'disponibili': len([g for g in giocatori if g['stato'] == 'disponibile']),
        'tuoi': len([g for g in giocatori if g['stato'] == 'tuo']),
        'avversari': len([g for g in giocatori if g['stato'] == 'avversario']),
        'budget_residuo': consigli_engine.budget_rimasto
    }
    
    return render_template('listone.html', 
                         giocatori=giocatori, 
                         stats=stats,
                         suggerimento_top=suggerimento_top)

@app.route('/segna_avversario', methods=['POST'])
def segna_avversario():
    nome = request.form.get('nome')
    if nome:
        consigli_engine.segna_avversario(nome)
    return redirect('/listone')

@app.route('/rimuovi_avversario', methods=['POST'])
def rimuovi_avversario():
    nome = request.form.get('nome')
    if nome:
        consigli_engine.rimuovi_avversario(nome)
    return redirect('/listone')

@app.route('/reset_asta')
def reset_asta():
    global gestione_asta
    if gestione_asta:
        gestione_asta.resetta()
    return redirect('/dashboard')
if __name__ == '__main__':
    print("🚀 Avvio server...")
    print("🌐 Apri il browser su: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

@app.route('/rimuovi_acquisto', methods=['POST'])
def rimuovi_acquisto():
    global gestione_asta
    nome = request.form.get('nome')
    ruolo = request.form.get('ruolo')
    squadra = request.form.get('squadra')

    if nome and gestione_asta:
        risultato = gestione_asta.rimuovi_acquisto(nome, ruolo, squadra)
        return redirect('/dashboard?messaggio=' + risultato.get('message', ''))
    
    return redirect('/dashboard')

@app.route('/esporta_squadra', methods=['POST'])
def esporta_squadra():
    global gestione_asta
    if not gestione_asta:
        return redirect('/dashboard')
    
    # Crea un testo con la squadra
    testo = "🏆 SQUADRA FANTACALCIO\n"
    testo += "="*40 + "\n\n"
    
    for ruolo in ['P', 'D', 'C', 'A']:
        nome_ruolo = {'P':'Portieri','D':'Difensori','C':'Centrocampisti','A':'Attaccanti'}[ruolo]
        testo += f"📌 {nome_ruolo}:\n"
        acquistati = [a for a in gestione_asta.acquisti if a['ruolo'] == ruolo]
        for a in acquistati:
            testo += f"  - {a['nome']} ({a['squadra']}) - {a['costo']}M\n"
        testo += "\n"
    
    testo += f"\n💰 Budget totale: {gestione_asta.budget_totale}M\n"
    testo += f"💰 Budget residuo: {gestione_asta.budget_residuo}M\n"
    testo += f"💸 Speso: {gestione_asta.budget_totale - gestione_asta.budget_residuo}M\n"
    
    # Crea una risposta di testo
    from flask import Response
    return Response(testo, mimetype='text/plain', headers={
        'Content-Disposition': 'attachment;filename=squadra_fantacalcio.txt'
    })
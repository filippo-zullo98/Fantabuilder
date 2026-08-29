# main.py - Motore di consigli per asta fantacalcio
import csv
import json
import os
from typing import List, Dict, Optional

class Giocatore:
    def __init__(self, nome: str, ruolo: str, squadra: str, quotazione: float, 
                 fantamedia: float, gol: int, assist: int, voto_medio: float, note: str = ""):
        self.nome = nome
        self.ruolo = ruolo
        self.squadra = squadra
        self.quotazione = quotazione
        self.fantamedia = fantamedia
        self.gol = gol
        self.assist = assist
        self.voto_medio = voto_medio
        self.note = note
        
    def calcola_indice(self) -> float:
        moltiplicatore_ruolo = 1.0
        if self.ruolo == 'A':
            moltiplicatore_ruolo = 1.3
        elif self.ruolo == 'C':
            moltiplicatore_ruolo = 1.1
        elif self.ruolo == 'D':
            moltiplicatore_ruolo = 0.9
        elif self.ruolo == 'P':
            moltiplicatore_ruolo = 0.8
            
        penalita = 0
        if 'infortuni' in self.note.lower():
            penalita = 0.3
        elif 'squalifica' in self.note.lower():
            penalita = 0.2
            
        valore = (self.fantamedia * 2 + self.gol * 3 + self.assist * 2 + self.voto_medio)
        costo = self.quotazione + 0.5
        
        indice = (valore * moltiplicatore_ruolo / costo) - penalita
        return round(indice, 2)
    
    def to_dict(self) -> Dict:
        return {
            'nome': self.nome,
            'ruolo': self.ruolo,
            'squadra': self.squadra,
            'quotazione': self.quotazione,
            'fantamedia': self.fantamedia,
            'gol': self.gol,
            'assist': self.assist,
            'voto_medio': self.voto_medio,
            'indice': self.calcola_indice(),
            'note': self.note
        }


class ConsigliAsta:
    def __init__(self):
        self.giocatori: List[Giocatore] = []
        self.acquistati: List[str] = []
        self.budget_rimasto: float = 500
        self.gestione_asta = None
        self.giocatori_avversari: List[Giocatore] = []  # Lista dei giocatori acquistati dagli avversari
        self.stato_file = 'stato_asta.json'
        self.carica_stato()

    def carica_stato(self):
        """Carica los stato dell'asta da file"""
        if os.path.exists(self.stato_file):
            try:
                with open(self.stato_file):
                    data = json.load(f)
                    self.acquistati = data.get('acquistati', [])
                    self.giocatori_avversari = data.get('giocatori_avversari', [])
                    self.budget_rimasto = data.get('budget_rimasto', 500)
                    print(f"✅ Stato dell'asta caricato da {self.stato_file}")
            except:
                print(f"❌ Errore nel caricamento dello stato")

    def salva_stato(self):
        """Salva lo stato dell'asta su file"""
        data = {
            'acquistati': self.acquistati,
            'giocatori_avversari': self.giocatori_avversari,
            'budget_rimasto': self.budget_rimasto
        }

        with open(self.stato_file, 'w') as f:
            json.dump(data, f, indent=2)

    def carica_da_csv(self, file_path: str) -> None:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    giocatore = Giocatore(
                        nome=row['nome'].strip(),
                        ruolo=row['ruolo'].strip(),
                        squadra=row['squadra'].strip(),
                        quotazione=float(row['quotazione']),
                        fantamedia=float(row['fantamedia']),
                        gol=int(row['gol']),
                        assist=int(row['assist']),
                        voto_medio=float(row['voto_medio']),
                        note=row.get('note', '').strip()
                    )
                    self.giocatori.append(giocatore)
            print(f"✅ Caricati {len(self.giocatori)} giocatori")
        except FileNotFoundError:
            print(f"❌ File {file_path} non trovato!")
        except Exception as e:
            print(f"❌ Errore: {e}")
    
    def filtra_ruolo(self, ruolo: Optional[str] = None) -> List[Giocatore]:
        if not ruolo or ruolo == 'tutti':
            return self.giocatori
        return [g for g in self.giocatori if g.ruolo == ruolo]
    
    def escludi_acquistati(self, giocatori: List[Giocatore]) -> List[Giocatore]:
        return [g for g in giocatori if g.nome not in self.acquistati]
    
    def suggerisci(self, ruolo: Optional[str] = None, budget: Optional[float] = None,
                escludi: List[str] = [], top_n: int = 10) -> List[Dict]:
        # 1. Filtra per ruolo
        candidati = self.filtra_ruolo(ruolo)
        
        # 2. Crea la lista completa di giocatori da escludere (tuoi + avversari + escludi passati)
        escludi_completa = set(self.acquistati + self.giocatori_avversari + escludi)
        
        # 3. Escludi tutti i giocatori nella lista
        candidati = [g for g in candidati if g.nome not in escludi_completa]
        
        # 4. Filtra per budget
        if budget is not None:
            candidati = [g for g in candidati if g.quotazione <= budget]
        
        # 5. Ordina per indice decrescente
        candidati.sort(key=lambda x: x.calcola_indice(), reverse=True)
        
        # 6. Restituisci i top N
        return [g.to_dict() for g in candidati[:top_n]]
    
    def suggerisci_per_ruolo(self, budget: float) -> Dict[str, List[Dict]]:
        risultati = {}
        for ruolo in ['P', 'D', 'C', 'A']:
            risultati[ruolo] = self.suggerisci(ruolo=ruolo, budget=budget, top_n=5)
        return risultati
    
    def strategia_asta(self, budget_totale: float, posti_per_ruolo: Dict[str, int]) -> Dict:
        pesi = {'A': 0.35, 'C': 0.30, 'D': 0.20, 'P': 0.15}
        budget_per_ruolo = {}
        suggerimenti = {}
        spesa_totale = 0
        
        for ruolo, posti in posti_per_ruolo.items():
            budget_per_ruolo[ruolo] = round(budget_totale * pesi.get(ruolo, 0.25), 2)
            suggerimenti[ruolo] = self.suggerisci(
                ruolo=ruolo, 
                budget=budget_per_ruolo[ruolo], 
                top_n=posti + 2
            )
            spesa_totale += sum([g['quotazione'] for g in suggerimenti[ruolo][:posti]])
        
        return {
            'budget_per_ruolo': budget_per_ruolo,
            'suggerimenti': suggerimenti,
            'spesa_stimata': round(spesa_totale, 2),
            'budget_residuo': round(budget_totale - spesa_totale, 2)
        }
    
    def aggiorna_acquistato(self, nome_giocatore: str) -> None:
        if nome_giocatore not in self.acquistati:
            self.acquistati.append(nome_giocatore)
    
    def rimuovi_acquistato(self, nome_giocatore: str) -> None:
        if nome_giocatore in self.acquistati:
            self.acquistati.remove(nome_giocatore)
    
    def resetta(self) -> None:
        self.acquistati = []
        if self.gestione_asta:
            self.gestione_asta.resetta()
    
    def init_gestione(self):
        """Inizializza la gestione dell'asta"""
        self.gestione_asta = GestioneAsta(self.budget_rimasto)
        self.gestione_asta.tool = self
        return self.gestione_asta

    def segna_avversario(self, nome_giocatore: str) -> None:
        """Segna un giocatore come preso dagli avversari"""
        if nome_giocatore not in self.giocatori_avversari:
            self.giocatori_avversari.append(nome_giocatore)
            print(f"🔴 Segnato avversario: {nome_giocatore}")

    def rimuovi_avversario(self, nome_giocatore: str) -> None:
        """Rimuove un giocatore dalla lista degli avversari (in caso di errore)"""
        if nome_giocatore in self.giocatori_avversari:
            self.giocatori_avversari.remove(nome_giocatore)

    def get_stato_giocatore(self, nome: str) -> str:
        """Restituisce lo stato di un giocatore: 'tuo', 'avversario', 'disponibile'"""
        if nome in self.acquistati:
            return 'tuo'
        elif nome in self.giocatori_avversari:
            return 'avversario'
        else:
            return 'disponibile'

class GestioneAsta:
    def __init__(self, budget_totale=500):
        self.budget_totale = budget_totale
        self.budget_residuo = budget_totale
        self.acquisti = []  # Lista di dict: {'nome': 'Sommer', 'ruolo': 'P', 'squadra': 'Inter', 'costo': 50}
        self.portieri_automatici = []  # Portieri presi automaticamente (regola squadra)
        self.fase_corrente = 'P'  # P, D, C, A
        self.ordine_fasi = ['P', 'D', 'C', 'A']
        self.tool = None
        
    def aggiungi_acquisto(self, nome, ruolo, squadra, costo, quotazione_base=0, automatico=False):
        """Aggiunge un acquisto, gestendo anche i portieri automatici con i loro costi base"""
        
        # Verifica se si può ancora acquistare per questo ruolo
        if not automatico and not self.puoi_acquistare(ruolo):
            return {
                'success': False,
                'message': f"❌ Hai già raggiunto il limite di {self.get_limiti_ruolo().get(ruolo)} {self._get_fase_nome(ruolo).lower()}!"
            }
        
        # Aggiungi l'acquisto principale
        acquisto = {
            'nome': nome,
            'ruolo': ruolo,
            'squadra': squadra,
            'costo': costo,  # Prezzo effettivo pagato all'asta
            'quotazione_base': quotazione_base,
            'automatico': automatico
        }
        self.acquisti.append(acquisto)
        self.budget_residuo -= costo
        
        # REGOLA PORTIERI: se acquisti un portiere (NON automatico), prendi tutti gli altri della stessa squadra
        portieri_aggiunti = []
        costo_totale_automatici = 0
        
        if ruolo == 'P' and not automatico:
            print(f"🔍 Cerco portieri della squadra: {squadra}")
            
            # Cerca tutti i portieri della stessa squadra nel database
            for g in self.tool.giocatori:
                if g.ruolo == 'P' and g.squadra == squadra and g.nome != nome:
                    print(f"  - Trovato: {g.nome} (quotazione base: {g.quotazione})")
                    
                    # Verifica se questo portiere è già stato acquistato
                    if not self.portiere_acquistato(g.nome, squadra):
                        # Verifica che ci sia ancora spazio per portieri automatici
                        if self.puoi_acquistare('P'):
                            # Prezzo: usa la quotazione base del giocatore
                            costo_automatico = g.quotazione
                            print(f"    ✅ Aggiunto automaticamente: {g.nome} al costo di {costo_automatico}M")
                            
                            # Aggiungi il portiere automatico
                            self.acquisti.append({
                                'nome': g.nome,
                                'ruolo': 'P',
                                'squadra': squadra,
                                'costo': costo_automatico,  # Prezzo base
                                'quotazione_base': costo_automatico,
                                'automatico': True
                            })
                            
                            # Sottrai il costo dal budget
                            self.budget_residuo -= costo_automatico
                            costo_totale_automatici += costo_automatico
                            
                            # Tienilo traccia per il messaggio
                            portieri_aggiunti.append(f"{g.nome} ({costo_automatico}M)")
                        else:
                            print(f"    ⚠️ Non posso aggiungere {g.nome} - limite portieri raggiunto!")
                            break
                    else:
                        print(f"    ⚠️ {g.nome} già acquistato")
        
        # Costruisci il messaggio di risposta
        messaggio = f"✅ Acquistato {nome} per {costo}M"
        
        if portieri_aggiunti:
            messaggio += f"\n🔄 Inclusi automaticamente: {', '.join(portieri_aggiunti)}"
            messaggio += f"\n💰 Costo totale portieri: {costo + costo_totale_automatici}M"
        
        return {
            'success': True,
            'message': messaggio
        }        
    def portiere_acquistato(self, nome, squadra):
        """Verifica se un portiere è già stato acquistato (anche automaticamente)"""
        for a in self.acquisti:
            if a['nome'] == nome and a['squadra'] == squadra:
                return True
        return False
    
    def get_acquistati_ruolo(self, ruolo):
        """Restituisce i nomi dei giocatori acquistati per un dato ruolo"""
        return [a['nome'] for a in self.acquisti if a['ruolo'] == ruolo]
    
    def get_acquistati_squadra(self, squadra):
        """Restituisce i nomi dei giocatori acquistati per una data squadra"""
        return [a['nome'] for a in self.acquisti if a['squadra'] == squadra]
    
    def get_consigli_fase(self, top_n=5):
        """Restituisce i migliori consigli per la fase corrente"""
        # Escludi tutti i giocatori già acquistati (anche automatici)
        escludi = [a['nome'] for a in self.acquisti]
        
        # Filtra per ruolo corrente
        consigli = self.tool.suggerisci(
            ruolo=self.fase_corrente,
            budget=self.budget_residuo,
            escludi=escludi,
            top_n=top_n
        )
        
        # Aggiungi informazioni extra per ogni consiglio
        for c in consigli:
            # Verifica se c'è un portiere automatico disponibile
            if self.fase_corrente == 'P':
                # Trova portieri della stessa squadra non ancora acquistati
                portieri_squadra = []
                for g in self.tool.giocatori:
                    if g.ruolo == 'P' and g.squadra == c['squadra'] and g.nome != c['nome']:
                        if not self.portiere_acquistato(g.nome, g.squadra):
                            portieri_squadra.append(g.nome)
                if portieri_squadra:
                    c['portieri_automatici'] = portieri_squadra
                    c['suggerimento'] = f"Acquistando {c['nome']} prenderai anche: {', '.join(portieri_squadra)} (gratis!)"
        
        return consigli
    
    def get_statistiche(self):
        """Restituisce statistiche sull'asta"""
        totale_speso = self.budget_totale - self.budget_residuo
        
        # Calcola il costo totale per ruolo
        costi_per_ruolo = {}
        for ruolo in ['P', 'D', 'C', 'A']:
            costi_per_ruolo[ruolo] = sum([
                a['costo'] for a in self.acquisti 
                if a['ruolo'] == ruolo
            ])
        
        stats = {
            'budget_totale': self.budget_totale,
            'budget_residuo': self.budget_residuo,
            'speso': totale_speso,
            'percentuale_spesa': round((totale_speso / self.budget_totale) * 100, 1),
            'fase_corrente': self.fase_corrente,
            'fase_nome': self._get_fase_nome(self.fase_corrente),
            'totale_acquisti': len(self.acquisti),
            'portieri_automatici': len([a for a in self.acquisti if a.get('automatico', False)]),
            'costi_per_ruolo': costi_per_ruolo,
            'limiti': {}
        }
        
        # Aggiungi statistiche per ogni ruolo con i limiti
        for ruolo in ['P', 'D', 'C', 'A']:
            attuali = self.get_acquistati_per_ruolo(ruolo)
            limite = self.get_limiti_ruolo().get(ruolo, 0)
            stats[ruolo.lower()] = attuali
            stats['limiti'][ruolo] = {
                'attuali': attuali,
                'limite': limite,
                'rimanenti': limite - attuali,
                'costo_totale': costi_per_ruolo.get(ruolo, 0)
            }
        
        return stats
    
    def _get_fase_nome(self, ruolo):
        mappa = {'P': 'Portieri', 'D': 'Difensori', 'C': 'Centrocampisti', 'A': 'Attaccanti'}
        return mappa.get(ruolo, '')
    
    def avanza_fase(self):
        """Passa alla prossima fase dell'asta"""
        indice_corrente = self.ordine_fasi.index(self.fase_corrente)
        if indice_corrente < len(self.ordine_fasi) - 1:
            self.fase_corrente = self.ordine_fasi[indice_corrente + 1]
            return True
        return False  # Asta finita
    
    def resetta(self):
        """Resetta l'asta"""
        self.acquisti = []
        self.portieri_automatici = []
        self.budget_residuo = self.budget_totale
        self.fase_corrente = 'P'

    def get_limiti_ruolo(self):
        """Restituisce i limiti massimi per ruolo"""
        return {
            'P': 3,  # Portieri: max 3
            'D': 8,  # Difensori: max 8
            'C': 8,  # Centrocampisti: max 8
            'A': 6   # Attaccanti: max 6
        }
    
    def get_acquistati_per_ruolo(self, ruolo):
        """Restituisce il numero di giocatori acquistati per un ruolo"""
        return len([a for a in self.acquisti if a['ruolo'] == ruolo])
    
    def puoi_acquistare(self, ruolo):
        """Verifica se puoi ancora acquistare giocatori per questo ruolo"""
        limite = self.get_limiti_ruolo().get(ruolo, 0)
        attuali = self.get_acquistati_per_ruolo(ruolo)
        return attuali < limite
    
    def get_rimanenti_per_ruolo(self, ruolo):
        """Restituisce quanti giocatori puoi ancora acquistare per un ruolo"""
        limite = self.get_limiti_ruolo().get(ruolo, 0)
        attuali = self.get_acquistati_per_ruolo(ruolo)
        return limite - attuali  

    def rimuovi_acquisto(self, nome, ruolo, squadra):
        """Rimuove un acquisto (utile per sostituzioni)"""
        # Trova l'acquisto da rimuovere
        for i, a in enumerate(self.acquisti):
            if a['nome'] == nome and a['ruolo'] == ruolo and a['squadra'] == squadra:
                # Se è automatico, lo rimuoviamo solo se il portiere principale viene rimosso
                if a.get('automatico', False):
                    # Non rimuovere singoli portieri automatici
                    # Rimuoviamo solo il portiere principale e tutti i suoi automatici
                    pass
                
                # Rimuovi l'acquisto
                costo = a['costo']
                del self.acquisti[i]
                self.budget_residuo += costo
                
                # Se è un portiere, rimuovi anche gli automatici della stessa squadra
                if a['ruolo'] == 'P' and not a.get('automatico', False):
                    # Rimuovi i portieri automatici della stessa squadra
                    self.acquisti = [
                        a for a in self.acquisti 
                        if not (a['ruolo'] == 'P' and a['squadra'] == squadra and a.get('automatico', False))
                    ]
                    # Aggiorna i portieri automatici
                    self.portieri_automatici = [
                        p for p in self.portieri_automatici 
                        if p['squadra'] != squadra
                    ]
                
                return {
                    'success': True,
                    'message': f"✅ Rimosso {nome}!"
                }
        
        return {
            'success': False,
            'message': f"❌ Giocatore {nome} non trovato!"
        }
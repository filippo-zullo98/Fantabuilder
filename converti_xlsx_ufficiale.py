import pandas as pd
import re
import os

def estrai_numero(valore):
    """Estrae un numero da stringhe tipo '6.5' o '65' o 'nd'"""
    if pd.isna(valore):
        return 0
    if isinstance(valore, (int, float)):
        return float(valore)
    if isinstance(valore, str):
        valore = valore.strip()
        # Cerca un numero nel testo
        match = re.search(r'(\d+\.?\d*)', valore)
        if match:
            return float(match.group(1))
    return 0

def normalizza_ruolo(ruolo):
    """Normalizza il ruolo in P, D, C, A"""
    if pd.isna(ruolo):
        return ''
    ruolo = str(ruolo).strip().upper()
    if ruolo in ['P', 'D', 'C', 'A']:
        return ruolo
    if ruolo in ['POR', 'PORTIERE']:
        return 'P'
    if ruolo in ['DIF', 'DIFENSORE']:
        return 'D'
    if ruolo in ['CEN', 'CENTROCAMPISTA']:
        return 'C'
    if ruolo in ['ATT', 'ATTACCANTE']:
        return 'A'
    return ''

def converti_xlsx_in_csv(nome_file_xlsx):
    """Converte il file Excel ufficiale di Fantacalcio.it in CSV per il tool"""
    
    # Verifica che il file esista
    if not os.path.exists(nome_file_xlsx):
        print(f"❌ File {nome_file_xlsx} non trovato!")
        print("📁 Assicurati che il file Excel sia nella stessa cartella")
        return False
    
    try:
        # Leggi il file Excel saltando la prima riga (che è il titolo)
        df = pd.read_excel(nome_file_xlsx, header=1)
        
        print(f"✅ File {nome_file_xlsx} caricato con successo!")
        print(f"📊 Colonne trovate: {list(df.columns)}")
        print(f"📊 Righe totali: {len(df)}")
        
        # Crea il nuovo DataFrame con le colonne del tool
        df_convertito = pd.DataFrame()
        
        # Mappa delle colonne (nomi reali del file)
        mappa = {
            'nome': 'Nome',
            'ruolo': 'R',
            'squadra': 'Squadra',
            'quotazione': 'Qt.I',
            'fantamedia': 'FVM',
        }
        
        # Applica la mappa
        for col_dest, col_orig in mappa.items():
            if col_orig in df.columns:
                df_convertito[col_dest] = df[col_orig]
            else:
                print(f"⚠️ Colonna '{col_orig}' non trovata! Sarà vuota.")
                df_convertito[col_dest] = ''
        
        # Converti le colonne numeriche
        df_convertito['quotazione'] = df_convertito['quotazione'].apply(estrai_numero)
        df_convertito['fantamedia'] = df_convertito['fantamedia'].apply(estrai_numero)
        
        # Se la fantamedia è 0, usa un valore di default
        df_convertito['fantamedia'] = df_convertito['fantamedia'].fillna(6.0)
        
        # Aggiungi colonne mancanti
        df_convertito['gol'] = 0
        df_convertito['assist'] = 0
        df_convertito['voto_medio'] = df_convertito['fantamedia']
        df_convertito['note'] = ''
        
        # Normalizza il ruolo
        df_convertito['ruolo'] = df_convertito['ruolo'].apply(normalizza_ruolo)
        
        # Controlla se ci sono giocatori senza ruolo
        senza_ruolo = df_convertito[df_convertito['ruolo'] == '']
        if len(senza_ruolo) > 0:
            print(f"\n⚠️ ATTENZIONE: {len(senza_ruolo)} giocatori senza ruolo!")
        
        # Salva come CSV nella cartella data
        output_file = 'data/giocatori.csv'
        os.makedirs('data', exist_ok=True)
        df_convertito.to_csv(output_file, index=False, encoding='utf-8')
        
        print(f"\n✅ Conversione completata! File creato: {output_file}")
        print(f"📊 Giocatori convertiti: {len(df_convertito)}")
        print(f"\n🔍 Anteprima dei primi 5 giocatori:")
        print(df_convertito[['nome', 'ruolo', 'squadra', 'quotazione', 'fantamedia']].head(5))
        
        return True
        
    except Exception as e:
        print(f"❌ ERRORE durante la conversione: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔄 CONVERTITORE EXCEL -> CSV PER FANTACALCIO")
    print("=" * 60)
    print()
    
    # Cerca il file Excel
    nome_file = None
    for file in os.listdir('.'):
        if file.endswith('.xlsx') and 'Quotazioni' in file:
            nome_file = file
            break
    
    if nome_file:
        print(f"📁 Trovato: {nome_file}")
        converti_xlsx_in_csv(nome_file)
    else:
        print("❌ Nessun file Excel trovato nella cartella!")
        print("📁 Metti il file Excel delle quotazioni nella cartella corrente")
        print("📁 Il file di solito si chiama: Quotazioni_Fantacalcio_Stagione_2026_27.xlsx")
        
        # Chiedi il nome del file
        nome_inserito = input("\n🔍 Inserisci il nome del file Excel: ")
        if nome_inserito:
            converti_xlsx_in_csv(nome_inserito.strip())

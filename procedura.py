#!/usr/bin/env python
# -*- coding: utf-8 -*-
from psychopy import visual, event, core, gui, monitors
import random
import os
import csv
import yaml 

# Wczytanie pliku konfiguracyjnego
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)


# === KONFIGURACJA MONITORA ===
monitor_name = 'testMonitor'
if monitor_name not in monitors.getAllMonitors():
    mon = monitors.Monitor(monitor_name)
    mon.setWidth(config['monitor']['width_cm'])  # Szerokość ekranu w cm
    mon.setDistance(config['monitor']['distance_cm'])  # Odległość oczu od ekranu w cm
    mon.setSizePix(config['monitor']['resolution'])  # Rozdzielczość ekranu
    mon.save()

# === OKNO DIALOGOWE DLA UCZESTNIKA ===
info_dialog = gui.Dlg(title="Dane uczestnika")
info_dialog.addText('Proszę podać dane:')
info_dialog.addField('Identyfikator:')
info_dialog.addField('Wiek:')
info_dialog.addField('Płeć:', choices=['Kobieta', 'Mężczyzna', 'Inna'])
wynik_dialog = info_dialog.show()

if not info_dialog.OK:
    core.quit() #Zakończenie programu, gdy okno dialogowe zostaje anulowane

PART_ID = wynik_dialog[0] #ID uczestnika, użuwane do zapisu danych
wiek = wynik_dialog[1]
plec = wynik_dialog[2]

# === PARAMETRY EKSPERYMENTU ===
win = visual.Window(fullscr=config['window']['fullscreen'],
                    color=config['window']['color'],
                    units=config['window']['units'],
                    monitor=monitor_name)
n_blocks = config['blocks']['count']  # Liczba bloków wyświetlanych w zadaniu
block_size = config['blocks']['size']  # Rozmiar bloków
RESULTS = []  # Lista przechowująca dane z każdej próby
MAX_ERRORS = config['experiment']['max_errors']  # Maksymalna liczba błędów, po której kończy się sesja

conf = {
    "BLOCK_COLOR_TRAINING": [[0.2, 0.2, 0.2]] * n_blocks,  # Ciemnoszare bloki w fazie treningowej
}

# === Przycisk ZAKOŃCZ – definiowany raz ===
done_cfg = config['buttons']['done']
done_button = visual.Rect(win, width=done_cfg['width'], height=done_cfg['height'],
                          pos=done_cfg['pos'],
                          fillColor=done_cfg['color_fill'],
                          lineColor=done_cfg['color_line'])
done_text = visual.TextStim(win, text=done_cfg['text']['content'], pos=done_cfg['pos'],
                            color=done_cfg['text']['color'],
                            height=done_cfg['text']['height'],
                            anchorHoriz='center', anchorVert='center')

# === FUNKCJE ===

# == GENEROWANIE POZYCJI BLOKÓW ==
def generate_non_overlapping_positions(n):
    """Losowanie n pozycji dla bloków na ekranie, tak aby na siebie nie nachodziły"""
    positions = []
    attempts = config['blocks']['attempts']
    margin_y = config['blocks']['margin_y'] # Margines przy górnej i dolnej krawędzi ekranu

    while len(positions) < n and attempts < config['blocks']['max_overlap_attempts']:
        x = random.uniform(-0.45, 0.45)
        y = random.uniform(-0.45 + margin_y, 0.45 - margin_y)
        pos = (x, y)

        # Sprawdzenie, czy położenie nowego bloku koliduje z położeniem już istniejących bloków
        overlap = False
        for px, py in positions:
            if abs(x - px) <= block_size * 1.2 and abs(y - py) <= block_size * 1.2:
                overlap = True
                break

        if not overlap:
            positions.append(pos)

        attempts += 1

    return positions

# == TWORZENIE BLOKÓW ==
def create_blocks(colors):
    """Tworzenie na ekranie bloków o podanych kolorach, w losowych, niekolidujących pozycjach"""
    positions = generate_non_overlapping_positions(n_blocks)
    blocks = []

    for i in range(n_blocks):
        rect = visual.Rect(win, width=block_size, height=block_size,
                           fillColor=colors[i], lineColor=colors[i],
                           pos=positions[i], name=f'block{i}')
        blocks.append(rect)

    return blocks

# === RYSOWANIE BLOKÓW I PRZYCISKU ZAKOŃCZ ===
def draw_blocks(blocks, draw_done_button=True):
    for b in blocks:
        b.draw()

    if draw_done_button:
        done_button.draw()
        done_text.draw()


def show_blocks(blocks):
    """Wyświetlenie bloków na ekranie"""
    draw_blocks(blocks)
    win.flip()

# === MIGANIE BLOKÓW WEDŁUG SEKWENCJI ===
def flash_sequence(blocks, sequence):
    """Wyświetlenie sekwencji migających bloków, zgodnie z daną kolejnością"""
    for i in sequence:
        orig_color = blocks[i].fillColor

        # Podświetlenie bloku
        blocks[i].fillColor = config['colors']['flash']
        blocks[i].lineColor = config['colors']['flash']
        draw_blocks(blocks)
        win.flip()
        core.wait(config['timing']['flash_on'])  # Czas podświetlenia bloku

        # Przywrócenie oryginalnego koloru
        blocks[i].fillColor = orig_color
        blocks[i].lineColor = orig_color
        draw_blocks(blocks)
        win.flip()
        core.wait(config['timing']['flash_off'])  # Przerwa między mignięciami

# === ZEBRANIE ODPOWIEDZI ===
def get_response(blocks, target_sequence, session_type="training"):
    """Pobranie odpowiedzi od uczestnika - kliknięcia, kolejność, czas odpowiedzi"""
    response = []
    clicked = set()
    mouse = event.Mouse(visible=True)
    rt_clock = core.Clock()
    inter_click_times = []

    rt_clock.reset()
    responded = False
    last_click_time = None

    while not responded:
        # Sprawdzanie klawiszy wyjścia
        keys = event.getKeys()
        if 'escape' in keys or 'q' in keys:
            win.close()
            core.quit()

        draw_blocks(blocks)
        win.flip()

        if mouse.getPressed()[0]:  # Lewy przycisk myszy
            # Sprawdzenie, czy kliknięto w blok
            for i, b in enumerate(blocks):
                if b.contains(mouse) and i not in clicked:
                    current_time = rt_clock.getTime()

                    # Zapis czasu między kliknięciami
                    if last_click_time is not None:
                        inter_click_times.append(current_time - last_click_time)
                    last_click_time = current_time

                    response.append(i)
                    clicked.add(i)

                    # Wizualna odpowiedź na kliknięcie - miganie bloku
                    orig_color = b.fillColor
                    b.fillColor = config['colors']['click']
                    b.lineColor = config['colors']['click']
                    draw_blocks(blocks)
                    win.flip()
                    core.wait(config['timing']['post_click_flash'])

                    # Przywrócenie oryginalnego koloru
                    b.fillColor = orig_color
                    b.lineColor = orig_color

                    # Sprawdź czy kliknięto przycisk ZAKOŃCZ
            if done_button.contains(mouse):
                responded = True
                core.wait(config['timing']['post_click_delay'])  # Zapobieganie podwójnemu kliknięciu

        core.wait(config['timing']['response_poll_interval'])

    rt = rt_clock.getTime() #Czas całkowity od początku do kliknięcia przycisku ZAKOŃCX
    correct = is_correct(target_sequence, response)

    # Wyświetlenie informacji zwrotnej dla uczestnika
    fb_cfg = config['feedback']
    feedback_text = visual.TextStim(win, text=fb_cfg['correct_text'] if correct else fb_cfg['incorrect_text'],
        pos=fb_cfg['position'],
        color=fb_cfg['color'],
        height=fb_cfg['height'],
        anchorHoriz='center', anchorVert='center')
    draw_blocks(blocks)
    feedback_text.draw()
    win.flip()
    core.wait(fb_cfg['display_time'])


    return response, rt, correct, inter_click_times

# === SPRAWDZENIE POPRAWNOŚCI ===
def is_correct(target, response):
    """Porównanie odpowiedzi uczestnika z sekwencją docelową i zwrócenie True jeśli idealnie się ze sobą pokrywają"""
    return target == response


def show_message(text, wait_for_key=True):
    """Wyświetlenie wiadomości tekstowej na ekranie, oczekiwanie na naciśnięcie spacji"""
    msg = visual.TextStim(win, text=text, color=config['colors']['text_default'], height=config['text']['default_height'], wrapWidth=config['text']['wrap_width'],
                          anchorHoriz='center', anchorVert='center')
    msg.draw()
    win.flip()
    if wait_for_key:
        event.waitKeys(keyList=['space'])


def show_ready_prompt():
    """Wyświetlenie komunikatu o gotowości do rozpoczęcia próby"""
    text = ("Zadanie zaraz się rozpocznie.\n\n"
            "Umieść dłoń na myszce, a palec nad lewym przyciskiem.\n\n"
            "Skup swój wzrok na ekranie i pamiętaj, żeby swoich odpowiedzi udzielać jak najszybciej i jak najdokładniej.\n\n"
            "Gdy będziesz gotowy/gotowa, naciśnij spację.")
    show_message(text)


def show_break(stage):
    """Wyświetlenie komunikatu informującego o zakończeniu etapu i zapowiadającego przerwę między etapami"""
    msg = visual.TextStim(win, text=f"Przerwa 5 sekund.\nEtap {stage} z 3 ukończony.",
                          color=config['colors']['text_default'], height=config['text']['default_height'], anchorHoriz='center', anchorVert='center')
    msg.draw()
    win.flip()
    core.wait(config['timing']['break_time'])


def run_sequence_phase(blocks, sequence):
    """Przebieg fazy prezentacji sekwencji bloków"""
    draw_blocks(blocks)
    win.flip()
    core.wait(config['timing']['pre_sequence_delay'])

    flash_sequence(blocks, sequence)

    # Wyświetlenie komunikatu "TERAZ", sygnalizującego moment rozpoczęcia odpowiedzi
    prompt = visual.TextStim(win, text=config['start']['text'], pos=config['start']['position'], color=config['start']['color'], height=config['start']['height'],
                             anchorHoriz='center', anchorVert='center')
    draw_blocks(blocks)
    prompt.draw()
    win.flip()
    core.wait(config['timing']['now_text_delay'])


# === WCZYTANIE INSTRUKCJI ===
try:
    with open('instrukcja.txt', 'r', encoding='utf-8') as f:
        instrukcja_text = f.read().format(PART_ID=PART_ID, plec=plec, wiek=wiek)

        # Wyświetlenie instrukcji z mniejszą czcionką
    instrukcja_stim = visual.TextStim(win, text=instrukcja_text,
                                      color=config['colors']['text_default'],
                                      height=config['text']['small_height'],  # Zmniejszona czcionka
                                      wrapWidth=config['text']['wrap_width'],
                                      anchorHoriz='center', anchorVert='center')
    instrukcja_stim.draw()
    win.flip()
    event.waitKeys(keyList=['space'])

except FileNotFoundError:
    show_message("Brak pliku z instrukcją (instrukcja.txt).\nSkontaktuj się z prowadzącym badanie.")
    win.close()
    core.quit()

# === FAZA TRENINGOWA ===
current_length = config['experiment']['initial_sequence_length']
blocks = create_blocks(conf["BLOCK_COLOR_TRAINING"])
show_message("Część treningowa", wait_for_key=False)
core.wait(config['timing']['session_name_delay'])
show_ready_prompt()

# 3 próby treningowe o rosnącąej trudności
for _ in range(config['experiment']['training_trials']):
    # Zabezpieczenie przed tworzeniem sekwencji dłuższych od liczby bloków
    if current_length > n_blocks:
        current_length = n_blocks

    sequence = random.sample(range(n_blocks), current_length)
    run_sequence_phase(blocks, sequence)
    resp, rt, correct, ict = get_response(blocks, sequence, session_type="training")

    # Zapis wyników
    RESULTS.append([
        PART_ID, wiek, plec, 0, '#808080', len(sequence),
        sequence, resp, correct, ict,
        len(ict) - sum([1 for x in ict if x > 10]), rt
    ])

    # Zwiększ trudność po poprawnym wykonaniu
    if correct:
        current_length += 1

show_break(1)

# === SESJE EKSPERYMENTALNE ===
# Losowanie kolejności kolorów bloków (czerwony/niebieski)
first_color = random.choice(['#FF0000', '#0000FF'])
second_color = '#0000FF' if first_color == '#FF0000' else '#FF0000'

for session_num, color in [(1, first_color), (2, second_color)]:
    consecutive_errors = 0
    current_length = config['experiment']['initial_sequence_length']  # Reset długości sekwencji
    blocks = create_blocks([color] * n_blocks)

    show_message(f"Sesja eksperymentalna {session_num}", wait_for_key=False)
    core.wait(config['timing']['session_name_delay'])
    show_ready_prompt()

    while consecutive_errors < MAX_ERRORS:
        # Zabezpieczenie przed sekwencjami dłuższymi niż liczba bloków
        if current_length > n_blocks:
            current_length = n_blocks

        sequence = random.sample(range(n_blocks), current_length)
        run_sequence_phase(blocks, sequence)
        resp, rt, correct, ict = get_response(blocks, sequence, f"experiment{session_num}")

        # Zapis wyników
        RESULTS.append([
            PART_ID, wiek, plec, session_num, color, len(sequence),
            sequence, resp, correct, ict, consecutive_errors, rt
        ])

        # Aktualizacja parametrów trudności
        if correct:
            if current_length < n_blocks:  # Nie zwiększaj powyżej maksimum
                current_length += 1
            consecutive_errors = 0 #Resetuj liczbę błędów po sukcesie
        else:
            consecutive_errors += 1

    if session_num == 1:
        show_break(2)

    # === PODSUMOWANIE ===
# Obliczenie zakresu pamięci (Corsi span) - długości najdłuższej poprawnie wskazanej sekwencji w każdej sesji
# Filtrowanie jedynie poprawnych odpowiedzi dla każdej sesji
#dlaczego row[6]  row[8]  itd -  to kolumna (czyli element listy row) w strukturze RESULTS
#default=0 to zabezpieczenie na wypadek, gdyby uczestnik nie miał żadnych poprawnych odpowiedzi – wtedy maksymalna wartość to 0, żeby nie było błędu w działaniu funkcji max().
span1 = max([len(row[6]) for row in RESULTS if row[3] == 1 and row[8]], default=0) #sesja pierwsza
span2 = max([len(row[6]) for row in RESULTS if row[3] == 2 and row[8]], default=0) #sesja druga
# row[3] - numer sesji (0-trening, 1-sesja1, 2-sesja2)
# row[6] - lista numerów bloków w sekwencji (np. [3,1,4])
# row[8] - czy odpowiedź była poprawna (True/False)
# len(...) - długość zaprezentowanej sekwencji
# max(...) - znalezienie najdłuższej pośród zaprezentowanych sekwencji

final_msg = (f"Zadanie zakończone\n\nTwój zakres pamięci (Corsi span):\n"
             f"Sesja 1 ({first_color}): {span1} elementów\n"
             f"Sesja 2 ({second_color}): {span2} elementów\n\n"
             "Dziękujemy za udział w badaniu!")
show_message(final_msg)

# === ZAPIS DANYCH ===
# Tworzenie pliku CSV, w któym zapisywane są dane
results_file = config['results']['file']
file_exists = os.path.isfile(results_file)

with open(results_file, 'a', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)

    # Dodanie nagłówku, jeśli plik nie istnieje
    if not file_exists:
        writer.writerow([config['results']['headers']])

    # Formatowanie danych przed zapisem:
    # - Sekwencje i odpowiedzi zamieniamy na stringi oddzielone myślnikami
    # - Czasy międzykliknięć formatujemy do 3 miejsc po przecinku
    # - Czas reakcji również formatujemy do 3 miejsc
    for row in RESULTS:
        writer.writerow([
            row[0],  # ID uczestnika
            row[1],  # Wiek
            row[2],  # Płeć
            row[3],  # Numer sesji
            row[4],  # Kolor bloków
            row[5],  # Długość sekwencji
            '-'.join(map(str, row[6])),  # Sekwencja
            '-'.join(map(str, row[7])) if row[7] else "Brak",  # Odpowiedź
            row[8],  # Poprawność
            '-'.join([f"{t:.3f}" for t in row[9]]) if row[9] else "Brak",  # Czasy między kliknięciami
            row[10],  # Błędy
            f"{row[11]:.3f}"  # Czas reakcji
        ])
win.close()
core.quit()

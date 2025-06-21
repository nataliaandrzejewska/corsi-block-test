#!/usr/bin/env python
# -*- coding: utf-8 -*-
from psychopy import visual, event, core, gui, monitors
import random
import os
import csv

# === KONFIGURACJA MONITORA ===
monitor_name = 'testMonitor'
if monitor_name not in monitors.getAllMonitors():
    mon = monitors.Monitor(monitor_name)
    mon.setWidth(53.0)  # Szerokość ekranu w cm
    mon.setDistance(60.0)  # Odległość oczu od ekranu w cm
    mon.setSizePix([1920, 1080])  # Rozdzielczość ekranu
    mon.save()

# === OKNO DIALOGOWE DLA UCZESTNIKA ===
info_dialog = gui.Dlg(title="Dane uczestnika")
info_dialog.addText('Proszę podać dane:')
info_dialog.addField('Identyfikator:')
info_dialog.addField('Wiek:')
info_dialog.addField('Płeć:', choices=['Kobieta', 'Mężczyzna', 'Inna'])
wynik_dialog = info_dialog.show()

if not info_dialog.OK:
    core.quit()

PART_ID = wynik_dialog[0]
wiek = wynik_dialog[1]
plec = wynik_dialog[2]

# === PARAMETRY EKSPERYMENTU ===
win = visual.Window(fullscr=True, color=[-1, -1, -1], units='height', monitor=monitor_name)
n_blocks = 9  # ilość bloków
block_size = 0.125  # rozmiar bloków
RESULTS = []  # wyniki
MAX_ERRORS = 2  # maksymalna liczba błędów

conf = {
    "BLOCK_COLOR_TRAINING": [[0.2, 0.2, 0.2]] * n_blocks,  # Ciemnoszare bloki
}

# === Przycisk ZAKOŃCZ – definiujemy raz ===
done_button = visual.Rect(win, width=0.25, height=0.1, pos=(0.6, -0.4),
                          fillColor='#FFFFFF', lineColor='#FFFFFF')
done_text = visual.TextStim(win, text="ZAKOŃCZ", pos=(0.6, -0.4),
                            color='#000000', height=0.04,
                            anchorHoriz='center', anchorVert='center')


def generate_non_overlapping_positions(n):
    """Generuje pozycje bloków bez nakładania się"""
    positions = []
    attempts = 0
    margin_y = 0.2  # Margines na górze i dole ekranu

    while len(positions) < n and attempts < 1000:
        x = random.uniform(-0.45, 0.45)
        y = random.uniform(-0.45 + margin_y, 0.45 - margin_y)
        pos = (x, y)

        # Sprawdzenie nakładania się z istniejącymi blokami
        overlap = False
        for px, py in positions:
            if abs(x - px) <= block_size * 1.2 and abs(y - py) <= block_size * 1.2:
                overlap = True
                break

        if not overlap:
            positions.append(pos)

        attempts += 1

    return positions


def create_blocks(colors):
    """Tworzy bloki na ekranie z podanymi kolorami"""
    positions = generate_non_overlapping_positions(n_blocks)
    blocks = []

    for i in range(n_blocks):
        rect = visual.Rect(win, width=block_size, height=block_size,
                           fillColor=colors[i], lineColor=colors[i],
                           pos=positions[i], name=f'block{i}')
        blocks.append(rect)

    return blocks


def draw_blocks(blocks, draw_done_button=True):
    """Rysuje bloki i przycisk ZAKOŃCZ na ekranie"""
    for b in blocks:
        b.draw()

    if draw_done_button:
        done_button.draw()
        done_text.draw()


def show_blocks(blocks):
    """Wyświetla bloki na ekranie"""
    draw_blocks(blocks)
    win.flip()


def flash_sequence(blocks, sequence):
    """Wyświetla sekwencję migających bloków"""
    for i in sequence:
        orig_color = blocks[i].fillColor

        # Podświetlenie bloku
        blocks[i].fillColor = '#FFFFFF'
        blocks[i].lineColor = '#FFFFFF'
        draw_blocks(blocks)
        win.flip()
        core.wait(0.6)  # Czas podświetlenia

        # Przywrócenie oryginalnego koloru
        blocks[i].fillColor = orig_color
        blocks[i].lineColor = orig_color
        draw_blocks(blocks)
        win.flip()
        core.wait(0.4)  # Przerwa między mignięciami


def get_response(blocks, target_sequence, session_type="training"):
    """Pobiera odpowiedź od uczestnika"""
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
            # Sprawdź czy kliknięto w blok
            for i, b in enumerate(blocks):
                if b.contains(mouse) and i not in clicked:
                    current_time = rt_clock.getTime()

                    # Zapisz czas między kliknięciami
                    if last_click_time is not None:
                        inter_click_times.append(current_time - last_click_time)
                    last_click_time = current_time

                    response.append(i)
                    clicked.add(i)

                    # Wizualna odpowiedź na kliknięcie
                    orig_color = b.fillColor
                    b.fillColor = '#FFFFFF'
                    b.lineColor = '#FFFFFF'
                    draw_blocks(blocks)
                    win.flip()
                    core.wait(0.2)

                    # Przywrócenie oryginalnego koloru
                    b.fillColor = orig_color
                    b.lineColor = orig_color

                    # Sprawdź czy kliknięto przycisk ZAKOŃCZ
            if done_button.contains(mouse):
                responded = True
                core.wait(0.3)  # Zapobieganie podwójnemu kliknięciu

        core.wait(0.01)

    rt = rt_clock.getTime()
    correct = is_correct(target_sequence, response)

    # Wyświetlenie informacji zwrotnej
    feedback_text = visual.TextStim(win, text="DOBRZE" if correct else "ŹLE",
                                    pos=(0.0, -0.4), color='#FFFFFF', height=0.05,
                                    anchorHoriz='center', anchorVert='center')
    draw_blocks(blocks)
    feedback_text.draw()
    win.flip()
    core.wait(2.0)

    return response, rt, correct, inter_click_times


def is_correct(target, response):
    """Sprawdza czy odpowiedź jest identyczna z sekwencją docelową"""
    return target == response


def show_message(text, wait_for_key=True):
    """Wyświetla wiadomość na ekranie"""
    msg = visual.TextStim(win, text=text, color='#FFFFFF', height=0.04, wrapWidth=0.9,
                          anchorHoriz='center', anchorVert='center')
    msg.draw()
    win.flip()
    if wait_for_key:
        event.waitKeys(keyList=['space'])


def show_ready_prompt():
    """Komunikat o gotowości do rozpoczęcia"""
    text = ("Zadanie zaraz się rozpocznie.\n\n"
            "Umieść dłoń na myszce, a palec nad lewym przyciskiem.\n\n"
            "Skup swój wzrok na ekranie i pamiętaj, żeby swoich odpowiedzi udzielać jak najszybciej i jak najdokładniej.\n\n"
            "Gdy będziesz gotowy/gotowa, naciśnij spację.")
    show_message(text)


def show_break(stage):
    """Ekran przerwy między etapami"""
    msg = visual.TextStim(win, text=f"Przerwa 5 sekund.\nEtap {stage} z 3 ukończony.",
                          color='#FFFFFF', height=0.04, anchorHoriz='center', anchorVert='center')
    msg.draw()
    win.flip()
    core.wait(5)


def run_sequence_phase(blocks, sequence):
    """Przebieg fazy prezentacji sekwencji"""
    draw_blocks(blocks)
    win.flip()
    core.wait(0.5)

    flash_sequence(blocks, sequence)

    # Wyświetlenie komunikatu "TERAZ"
    prompt = visual.TextStim(win, text="TERAZ", pos=(0.0, -0.4), color='#FFFFFF', height=0.06,
                             anchorHoriz='center', anchorVert='center')
    draw_blocks(blocks)
    prompt.draw()
    win.flip()
    core.wait(0.5)


# === WCZYTANIE INSTRUKCJI ===
try:
    with open('instrukcja.txt', 'r', encoding='utf-8') as f:
        instrukcja_text = f.read().format(PART_ID=PART_ID, plec=plec, wiek=wiek)

        # Wyświetlenie instrukcji z mniejszą czcionką
    instrukcja_stim = visual.TextStim(win, text=instrukcja_text,
                                      color='#FFFFFF',
                                      height=0.018,  # Zmniejszona czcionka
                                      wrapWidth=0.9,
                                      anchorHoriz='center', anchorVert='center')
    instrukcja_stim.draw()
    win.flip()
    event.waitKeys(keyList=['space'])

except FileNotFoundError:
    show_message("Brak pliku z instrukcją (instrukcja.txt).\nSkontaktuj się z prowadzącym badanie.")
    win.close()
    core.quit()

# === FAZA TRENINGOWA ===
current_length = 2
blocks = create_blocks(conf["BLOCK_COLOR_TRAINING"])
show_message("Część treningowa", wait_for_key=False)
core.wait(1.0)
show_ready_prompt()

# 3 próby treningowe z rosnącą trudnością
for _ in range(3):
    # Zabezpieczenie przed sekwencjami dłuższymi niż liczba bloków
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
# Losowanie kolejności kolorów
first_color = random.choice(['#FF0000', '#0000FF'])
second_color = '#0000FF' if first_color == '#FF0000' else '#FF0000'

for session_num, color in [(1, first_color), (2, second_color)]:
    consecutive_errors = 0
    current_length = 2  # Reset długości sekwencji
    blocks = create_blocks([color] * n_blocks)

    show_message(f"Sesja eksperymentalna {session_num}", wait_for_key=False)
    core.wait(1.0)
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
# Obliczenie zakresu pamięci (Corsi span)
span1 = max([len(row[6]) for row in RESULTS if row[3] == 1 and row[8]], default=0)
span2 = max([len(row[6]) for row in RESULTS if row[3] == 2 and row[8]], default=0)

final_msg = (f"Zadanie zakończone\n\nTwój zakres pamięci (Corsi span):\n"
             f"Sesja 1 ({first_color}): {span1} elementów\n"
             f"Sesja 2 ({second_color}): {span2} elementów\n\n"
             "Dziękujemy za udział w badaniu!")
show_message(final_msg)

# === ZAPIS DANYCH ===
results_file = "wyniki.csv"
file_exists = os.path.isfile(results_file)

with open(results_file, 'a', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)

    # Nagłówek jeśli plik nie istnieje
    if not file_exists:
        writer.writerow([
            "ID", "Wiek", "Płeć", "Sesja", "Kolor", "Długość sekwencji",
            "Prezentowane bloki", "Kliknięcia uczestnika", "Poprawność",
            "Czasy między kliknięciami", "Błędy", "Czas reakcji"
        ])

        # Zapis każdego wiersza wyników
    for row in RESULTS:
        writer.writerow([
            row[0], row[1], row[2], row[3], row[4], row[5],
            '-'.join(map(str, row[6])),  # Sekwencja
            '-'.join(map(str, row[7])) if row[7] else "Brak",  # Odpowiedź
            row[8],  # Poprawność
            '-'.join([f"{t:.3f}" for t in row[9]]) if row[9] else "Brak",  # Czasy między kliknięciami
            row[10],  # Błędy
            f"{row[11]:.3f}"  # Czas reakcji
        ])

win.close()
core.quit()

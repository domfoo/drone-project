---
layout: default
title: Remote-Kommunikation
---

# Remote-Kommunikation mit Drohne

Diese Dokumentation beschreibt die Kommunikation zwischen dem lokalen Computer und dem Raspberry Pi auf der Drohne.

## 1. Systemarchitektur
Das Drohensystem nutzt eine entkoppelte Architektur, bei der der lokale Computer die rechenintensive KI-Verarbeitung übernimmt. Dabei lassen sind drei Komponenten ausmachen:

![Systemarchitektur Diagramm](/assets/remote_comm_architecture_diagram.jpg)

* **Lokaler Computer:** Führt das KI-Modell *inference.py* aus und sendet Befehle via UDP. Die Klasse MissionController verbindet die KI-Erkennung und die Tastatursteuerung mit dem Raspberry Pi.

* **Raspberry Pi:** Empfängt Netzwerkpakete über drone_control_listener.py, hält einen MAVLink-Heartbeat mit dem Flight Controller (FC) aufrecht, leitet Signale an den FC weiter und steuert den Servo über GPIO.

* **Flight Controller:** Führt die Befehle für Flugmodi (Brake, Auto, RTL), das Scharfschalten der Motoren (Arming) und Abwurf-Servo aus.

## 2. Setup

### Computer-Konfiguration

* **Dependencies:** Installieren Sie Abhängigkeiten im *requirements.txt*.

### Raspberry Pi Konfiguration

* **Bridge-Skript:** *drone_control_listener.py* muss unter */home/tpu/* abgespeichert werden

* **Autostart-Einrichtung:** Erstellen Sie einen systemd-Dienst unter */etc/systemd/system/drone_bridge.service*, damit das Skript beim Booten automatisch startet.

* **Hardware-Verbindung:** Verbinden Sie den UART des Raspberry Pi (/dev/serial0) mit dem UART des Flight Controllers. Verbinden sie GPIO 18 mit dem Signalkabel des Servos.

## 3. Betriebsablauf (Bei jedem Flug)

### Schritt 1: Strom & Netzwerk

1. Verbinden Sie den lokalen Computer und den Raspberry Pi mit demselben Netzwerk (gleiches Subnetz).

```
WLAN-NAME: drohn3 
PASSWORT: geheim123
```

2. Ermitteln Sie die lokale IP-Adresse des Raspberry Pi.
3. Überprüfen Sie die Verbindung, indem Sie den Pi vom lokalen Computer aus anpingen.

### Schritt 2: FPV-Brille & Video-Verbindung

1. Verbinden Sie die Skyzone Cobra X FPV-Brille via USB mit dem lokalen Computer.
2. Stellen Sie sicher, dass der Kamera-Feed sichtbar ist (passen Sie die Videoquelle mit dem Parameter *source* an für `inference.py`).

### Schritt 3: Mission Control starten

1. Navigieren Sie auf dem Computer zu Ihrem Arbeitsverzeichnis und führen Sie aus:

```bash
# inference mit mission control aktiviert (default)
python3 inference.py --weights yolov8n_waste.pt --source 1

# mission control kann deaktiviert werden, wenn nur inference gewünscht ist
python3 inference.py --weights yolov8n_waste.pt --source 1 --no-mission
```

**Hinweis:** Die Kommunikationsbrücke ist über die Klasse MissionController in *inference.py* integriert. Sie verbindet KI-Erkennungen und Tastaturbefehle mit dem Raspberry Pi. Die Datei *mission_controller.py* enthält Hilfsfunktionen (*handle_detection*, *process_keypress*, *trigger_drone_action*).

## 4. Bedienung & Steuerung

### Manuelle Tastatur-Hotkeys

| Taste | Aktion/Flugmodus | Beschreibung |
|-----|-------------------|-------------------|
| a   | Arm (STABILIZE)   | Wechselt in STABILIZE und schaltet Motoren scharf |
| q   | Disarm            | Stoppt Motoren sofort (Vorsicht!) |
| b   | Brake             | Hält die Drohne an der aktuellen Position an |
| s   | Open Servo        | Löst den Abwurfmechanismus manuell aus |
| x   | Exit              | Schaltet den Mission Hub und die Bridge aus |
| j   | Stabilize MODE    | Wechselt in den manuellen Flug mit Selbstnivellierung |
| k   | Auto MODE         | Setzt den programmierten Missionsplan fort |
| l   | RTL MODE          | Rückkehr zum Startpunkt und Landung |

### Autonome Erkennungssequenz

Wenn die inference eine Mülldeponie erkennt, führt das Skript folgendes automatisch aus:

1. **Bremse (b):** Drohne stoppt die Bewegung.

2. **Abwurf (s):** Pi steuert den Servo an (Auf $\rightarrow$ 1s warten $\rightarrow$ Zu).

3. **Fortsetzen (k):** Drohne wechselt zurück in den AUTO-Modus, um die Mission fortzuführen.

Die Klasse *MissionController* übernimmt:

* Verarbeitung von Tastatureingaben für manuelle Steuerung.
* Überwachung der Erkennungsergebnisse des YOLOv8-Modells.
* Automatisches Auslösen der Abwurfsequenz bei Müll-Erkennung.
* Verwaltung von Abklingzeiten, um Mehrfachauslösungen zu verhindern.
* Sicherer Disarm der Drohne beim Beenden.

## 5. Fehlerbehebung

* **Skript-Updates:** Wenn Sie *drone_control_listener.py* aktualisieren, führen Sie sudo systemctl restart *drone_bridge.service* auf dem Pi aus.

* **Mission Control funktioniert nicht:** Prüfen Sie, ob das Flag --no-mission gesetzt ist.

* **Netzwerkverbindung:** Wenn Sie keine Befehle an den Pi senden können, prüfen Sie, ob beide im selben Subnetz sind (meist 172.20.10.x). Falls nicht, konfigurieren Sie IP-Adressen manuell:

    1. Manuelle Einrichtung

        | Name        | Wert                                      |
        |---------------------------|---------------------------------------------------------|
        | IP Adresse                | 172.20.10.15 (selbes Subnetz wie Pi)                      |
        | Subnetzmaske               | 255.255.255.0 (Subnetzmaske von *ifconfig en0 \| grep netmask*)                      |
        | Router                | 172.20.10.255 (broadcast von *ifconfig en0 \| grep netmask*)                      |

    2. Fügen Sie zu DNS Server hinzu: *172.20.10.1* & *8.8.8.8*

## 6. Code-Struktur

* **inference.py**: Hauptskript für YOLOv8-Inferenz und Mission Control.
* **mission_controller.py**: Enthält Hilfsfunktionen für Erkennung und Steuerung.
* **drone_control_listener.py**: Pi-Skript, das auf UDP-Befehle wartet und diese an den FC weiterleitet.
* **setup_test.py**: Test-Skript für die Systemvorraussetzungen des lokalen Computers

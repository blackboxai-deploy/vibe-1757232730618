# 📥 Comment récupérer le repository ?

## 🌐 Application Live
**URL actuelle**: https://sb-77oj8wxvv25e.vercel.run

## 💾 Récupération du Code Source

### Option 1: Téléchargement Direct (Recommandé)
Tous les fichiers sont disponibles dans ce sandbox Vercel. Vous pouvez:

1. **Accéder au dashboard Vercel** où ce sandbox est hébergé
2. **Télécharger les fichiers** individuellement depuis l'interface
3. **Copier le code** depuis les fichiers sources affichés

### Option 2: Recréation Locale

#### Étapes pour recréer l'application:

1. **Créer un nouveau dossier**:
   ```bash
   mkdir french-rental-hunter
   cd french-rental-hunter
   ```

2. **Copier les fichiers principaux** (dans cet ordre):
   - `requirements.txt` - Dépendances Python
   - `main.py` - Point d'entrée de l'application
   - `config/` - Configuration et paramètres
   - `database/` - Modèles de base de données
   - `scrapers/` - Framework de scraping
   - `communication/` - Automatisation des contacts
   - `web/` - Application web Flask
   - `utils/` - Utilitaires et helpers
   - `templates/` - Templates HTML
   - `.env.example` - Configuration d'exemple
   - `README.md` - Documentation complète

3. **Installation des dépendances**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configuration**:
   ```bash
   cp .env.example .env
   # Éditer .env avec vos paramètres
   ```

5. **Lancement**:
   ```bash
   python main.py
   ```

## 📂 Structure des Fichiers Essentiels

### Fichiers de Base (Obligatoires)
- ✅ `main.py` - Point d'entrée
- ✅ `requirements.txt` - Dépendances
- ✅ `.env` - Configuration

### Modules Core (Obligatoires)  
- ✅ `config/settings.py` - Configuration principale
- ✅ `database/models.py` - Modèles de données
- ✅ `web/app.py` - Application Flask
- ✅ `utils/logger.py` - Système de logs

### Scrapers (Fonctionnalité Principal)
- ✅ `scrapers/base_scraper.py` - Framework de base
- ✅ `scrapers/seloger_scraper.py` - Scraper SeLoger
- ✅ `scrapers/scheduler.py` - Planification automatique
- ✅ `utils/duplicate_detector.py` - Détection doublons

### Communication (Automatisation Contacts)
- ✅ `communication/email_sender.py` - Emails automatiques
- ✅ `communication/phone_caller.py` - Appels automatiques

### Interface Web (Dashboard)
- ✅ `templates/base.html` - Template de base
- ✅ `templates/dashboard.html` - Dashboard principal

## 🔧 Configuration Requise

### Variables d'Environnement Essentielles (.env)
```env
# Configuration Flask
SECRET_KEY=votre-clé-secrète
DEBUG=True
PORT=5000

# Configuration Email (Gmail recommandé)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=votre-email@gmail.com
SMTP_PASSWORD=votre-mot-de-passe-application
EMAIL_FROM=votre-email@gmail.com

# Critères de Recherche
SEARCH_CITIES=Paris,Lyon,Marseille
MAX_PRICE=1500
MIN_PRICE=500
PROPERTY_TYPES=apartment,studio

# Twilio (Optionnel pour appels)
TWILIO_ACCOUNT_SID=votre-sid
TWILIO_AUTH_TOKEN=votre-token
TWILIO_PHONE_NUMBER=+33123456789
```

## 🚀 Démarrage Rapide

### Minimal Setup (Test)
1. Copier seulement les fichiers essentiels
2. Installer: `pip install flask sqlalchemy beautifulsoup4 requests`
3. Créer `.env` avec configuration minimale
4. Lancer: `python main.py`

### Setup Complet (Production)
1. Copier tous les fichiers
2. Installer toutes les dépendances: `pip install -r requirements.txt`
3. Configurer email et Twilio dans `.env`
4. Activer le scheduler: `ENABLE_SCHEDULER=True`
5. Lancer: `python main.py`

## 📞 Support

### En cas de problème:
1. **Vérifiez les logs** dans le dossier `logs/`
2. **Testez la configuration** via `/settings` dans l'interface web
3. **Vérifiez les dépendances** avec `pip list`
4. **Consultez la documentation** dans `README.md`

### Dépannage courant:
- **Erreur d'import**: Vérifier que tous les fichiers sont présents
- **Erreur de base de données**: Le dossier `data/` sera créé automatiquement
- **Erreur email**: Utiliser un mot de passe d'application Gmail
- **Erreur scraping**: Commencer avec `ENABLE_SCHEDULER=False` pour tester

## 🎯 Prochaines Étapes

Une fois l'application récupérée et installée:

1. **Tester localement** avec votre configuration
2. **Configurer vos critères** de recherche
3. **Activer l'automatisation** une fois testé
4. **Surveiller les logs** pour optimiser
5. **Étendre avec de nouveaux scrapers** si nécessaire

---

## ✅ Application Fonctionnelle

L'application French Real Estate Rental Hunter est **entièrement fonctionnelle** et prête à l'utilisation pour automatiser votre recherche immobilière en France! 🇫🇷

**URL Live**: https://sb-77oj8wxvv25e.vercel.run
#!/bin/bash

# 🚀 Script de Déploiement GitHub pour French Real Estate Rental Hunter

echo "🏠 Déploiement French Real Estate Rental Hunter vers GitHub"
echo "================================================"

# Vérifier que nous sommes dans un repo git
if [ ! -d ".git" ]; then
    echo "❌ Erreur: Pas un repository Git. Lancez 'git init' d'abord."
    exit 1
fi

# Demander l'URL du repository GitHub
echo "📝 Veuillez entrer l'URL de votre repository GitHub :"
echo "   Exemple: https://github.com/votre-username/french-rental-hunter.git"
read -p "URL GitHub: " GITHUB_URL

if [ -z "$GITHUB_URL" ]; then
    echo "❌ URL GitHub requise"
    exit 1
fi

# Ajouter le remote origin (ou le mettre à jour)
echo "🔗 Configuration du remote origin..."
git remote remove origin 2>/dev/null
git remote add origin "$GITHUB_URL"

# Vérifier les fichiers à commiter
echo "📋 Fichiers prêts pour le commit:"
git status --porcelain | wc -l | xargs echo "   Fichiers:"

# Renommer la branche principale en 'main' (convention moderne)
echo "🌿 Renommage de la branche en 'main'..."
git branch -m master main

# Pousser vers GitHub
echo "⬆️ Upload vers GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 SUCCÈS! Repository créé sur GitHub"
    echo "📂 URL: $GITHUB_URL"
    echo "🌐 Votre application est maintenant disponible sur GitHub!"
    echo ""
    echo "📋 Prochaines étapes:"
    echo "   1. Allez sur $GITHUB_URL"
    echo "   2. Vérifiez que tous les fichiers sont présents"
    echo "   3. Editez le README si nécessaire"
    echo "   4. Invitez des collaborateurs si souhaité"
    echo ""
    echo "🚀 Application live toujours disponible:"
    echo "   https://sb-7ixntplw8tpc.vercel.run"
else
    echo "❌ Erreur lors de l'upload vers GitHub"
    echo "💡 Solutions possibles:"
    echo "   - Vérifiez l'URL du repository"
    echo "   - Assurez-vous d'avoir les permissions d'écriture"
    echo "   - Vérifiez votre authentification GitHub"
fi
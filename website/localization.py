"""Public interface translations and admin-editable bilingual content."""
from django.utils.translation import get_language

CONTENT_FIELDS = {
    'sitesettings': ('tagline', 'intro', 'address', 'visiting_address'),
    'teammember': ('role', 'extra_line', 'biography'),
    'practicearea': ('title', 'summary', 'body'),
    'practiceareasection': ('title', 'body'),
    'blogpost': ('title', 'excerpt', 'body'),
    'contentpage': ('title', 'lead', 'body'),
    'aboutsection': ('title', 'lead', 'body'),
    'contentblock': ('title', 'body'),
}

DUTCH = {
    'Would you like to know more?': 'Wilt u meer weten?',
    'Feel free to contact': 'Neem gerust contact op met',
    'Home': 'Home', 'About us': 'Over ons', 'Team': 'Team', 'Blog': 'Blog', 'MENU': 'MENU',
    'Practice areas': 'Rechtsgebieden', 'Our practice areas': 'Onze rechtsgebieden',
    'Vacancies': 'Vacatures', 'Social involvement': 'Maatschappelijke betrokkenheid',
    'Contact': 'Contact', 'Contact us': 'Neem contact op', 'Contact Us': 'Neem contact op',
    'CONTACT US': 'NEEM CONTACT OP', 'Terms & conditions': 'Algemene voorwaarden',
    'Privacy statement': 'Privacyverklaring', 'Disclaimer': 'Disclaimer', 'Cookie policy': 'Cookiebeleid',
    'Created by': 'Gemaakt door', 'Important networks': 'Belangrijke netwerken',
    'Meet the team': 'Ontmoet ons team', 'Our team': 'Ons team',
    'Please visit': 'Bezoek', 'for more information.': 'voor meer informatie.',
    'Legal solutions for entrepreneurs': 'Juridische oplossingen voor ondernemers',
    'Wolfs Advocaten. Legal solutions for entrepreneurs in Maastricht and abroad.': 'Wolfs Advocaten. Juridische oplossingen voor ondernemers in Maastricht en daarbuiten.',
    'Wolfs Advocaten is committed to advise clients in the best possible way.': 'Wolfs Advocaten zet zich in om cliënten zo goed mogelijk te adviseren.',
    'LEARN HOW': 'MEER WETEN?', 'EXPLORE': 'ONTDEK', 'PRACTICE AREAS': 'RECHTSGEBIEDEN',
    'How do we do it': 'Hoe doen we het', 'We analyse, we litigate,': 'We analyseren, we procederen,',
    'but we prefer to talk!': 'maar we praten liever!', 'LEARN MORE': 'LEES MEER', 'READ ALL': 'ALLES LEZEN',
    'International trade, Transport & logistics, Customs, Sanctions, Commercial advice & litigation, Corporate advice & litigation, Insurance, and Cannabis. Legal solutions for entrepreneurs.': 'Internationale handel, transport en logistiek, douanerecht, sancties, commercieel advies en procedures, ondernemingsrechtelijk advies en procedures, verzekeringsrecht en cannabisrecht. Juridische oplossingen voor ondernemers.',
    'Wolfs Advocaten believes in a practical approach to legal issues. We are realistic, creative and fast and we analyse the issue from different angles. Is the required solution feasible? Are (protracted) proceedings actually necessary? Our fundamental principle is teamwork: you are continuously consulted and provided with insight into the strategy to be chosen and its implementation.': 'Wolfs Advocaten gelooft in een praktische benadering van juridische vraagstukken. We zijn realistisch, creatief en snel en analyseren het vraagstuk vanuit verschillende invalshoeken. Is de gewenste oplossing haalbaar? Zijn (langdurige) procedures eigenlijk wel nodig? Ons uitgangspunt is teamwork: u wordt continu geraadpleegd en krijgt inzicht in de te kiezen strategie en de uitvoering daarvan.',
    'Wolfs Advocaten has a broad range of expertise when it comes to providing advice or conducting litigation in various areas of law.': 'Wolfs Advocaten beschikt over brede expertise voor advies en procedures op verschillende rechtsgebieden.',
    'Below is a brief explanation for each area of law. Issues also arise that are (or can be) covered by multiple areas of law, such as reviewing contracts or drafting general terms and conditions of business. Please': 'Hieronder vindt u een korte toelichting per rechtsgebied. Sommige vraagstukken raken meerdere rechtsgebieden, zoals het beoordelen van overeenkomsten of het opstellen van algemene voorwaarden. Neem gerust',
    'contact us': 'contact met ons op', 'if you have any questions.': 'als u vragen heeft.',
    'Below, you will find contact information from Wolfs Advocaten. We’d love to hear from you!': 'Hieronder vindt u de contactgegevens van Wolfs Advocaten. Wij horen graag van u!',
    'SUBMIT': 'VERZENDEN', 'Office': 'Kantoor', 'Maastricht office': 'Kantoor Maastricht',
    'Amsterdam visiting': 'Bezoekadres', 'address': 'Amsterdam',
    'First name': 'Voornaam', 'Last name': 'Achternaam', 'Email': 'E-mail', 'Phone': 'Telefoon', 'Message': 'Bericht',
    'Thank you. Your message has been received.': 'Bedankt. Uw bericht is ontvangen.',
    'Location:': 'Locatie:', 'Type:': 'Dienstverband:', 'Parttime / fulltime': 'Parttime / fulltime',
    'READ MORE >>>': 'LEES MEER >>>', 'Read more about': 'Lees meer over',
    'There are currently no open vacancies.': 'Er zijn momenteel geen openstaande vacatures.',
    'Wolfs speaking': 'Wolfs aan het woord', 'Articles are coming soon.': 'Binnenkort verschijnen hier artikelen.',
    'Share this article': 'Deel dit artikel',
    'Share on Facebook': 'Delen via Facebook', 'Share on X': 'Delen via X',
    'Share on LinkedIn': 'Delen via LinkedIn', 'Copy link': 'Link kopiëren',
    'Link copied': 'Link gekopieerd', 'Copy this link:': 'Kopieer deze link:',
    'All Posts': 'Alle berichten', '← All posts': '← Alle berichten',
    'Cannabis law': 'Cannabisrecht', 'International trade': 'Internationale handel',
    'Transport & logistics': 'Transport en logistiek', 'Customs law': 'Douanerecht',
    'OPEN DOCUMENT': 'OPEN DOCUMENT',
    'Previous slide': 'Vorige dia', 'Next slide': 'Volgende dia', 'Scroll to about us': 'Ga naar Over ons',
    'Logistics and transport': 'Logistiek en transport', 'Wolfs Advocaten consultation': 'Overleg bij Wolfs Advocaten',
    'Close menu': 'Menu sluiten', 'Site navigation': 'Navigatie', 'Main navigation': 'Hoofdnavigatie',
    'Wolfs Advocaten home': 'Wolfs Advocaten homepage', 'Wolfs Advocaten on LinkedIn': 'Wolfs Advocaten op LinkedIn',
    'Blog categories': 'Blogcategorieën', 'Blog pages': 'Blogpagina’s', 'First page': 'Eerste pagina',
    'Previous page': 'Vorige pagina', 'Next page': 'Volgende pagina', 'Last page': 'Laatste pagina',
    'About us — Wolfs Advocaten Maastricht': 'Over ons — Wolfs Advocaten Maastricht',
    'Attorney': 'Advocaat', 'Attorney - managing partner': 'Advocaat - managing partner',
    'Attorney / Founder': 'Advocaat / Oprichter', 'Jurist': 'Jurist', 'Paralegal': 'Juridisch medewerker',
    'Office manager': 'Officemanager', 'website dev': 'Websiteontwikkelaar',
}

def translate(text):
    return DUTCH.get(text, text) if (get_language() or 'en').startswith('nl') else text

def localized(obj, field):
    language = (get_language() or 'en').split('-')[0]
    value = getattr(obj, 'translations', {}).get(language, {}).get(field)
    if value is not None and value != '':
        return value
    return translate(getattr(obj, field, ''))

from datetime import date
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.management import call_command
from website.models import BlogPost, ContentPage, PracticeArea, SiteSettings, TeamMember

AREAS = [
('International trade','International trade law regulates the legal relations between traders, including how trade is conducted and how disputes are resolved.'),
('Transport & logistics','Transportation takes many forms: air, inland waterway, road and rail. Each has its own rules and industry conditions.'),
('Customs law','Every seller, importer, manufacturer, forwarder or carrier encounters customs sooner or later.'),
('Commercial advice & litigation','Commercial disputes can be resolved through negotiation, settlement, court proceedings or arbitration.'),
('Corporate advice & litigation','We advise on disputes between directors, shareholders and supervisory directors, aiming for a practical resolution.'),
('Liability law and insurance law','Company fires, cargo theft, professional errors and industrial accidents require clear advice on liability and coverage.'),
('Cannabis law','We advise entrepreneurs operating in the fast-changing regulated cannabis sector.'),
]
TEAM = [
('John Wolfs','Attorney - managing partner','j.wolfs@wolfsadvocaten.nl','team/john.jpg'),
('Maurice van Efferink','Attorney','info@wolfsadvocaten.nl','team/maurice.jpg'),
('Joost van den Akker','Jurist','info@wolfsadvocaten.nl','team/joost-van-den-akker-current-20261105.jpg'),
('Menno van Term','Paralegal','info@wolfsadvocaten.nl','team/menno.jpg'),
('Ella Delanty','Paralegal','info@wolfsadvocaten.nl','team/ella.jpg'),
('Vera Ubaghs','Office manager','info@wolfsadvocaten.nl','team/vera.jpg'),
('Romy Brüll','Office manager','info@wolfsadvocaten.nl','team/romy.jpg'),
('Ron Meulmeester','Attorney','ron.meulmeester@king-fisher.nl','team/ron.jpg'),
('Bas Janssen','Attorney','janssen@bj-advocatuur.nl','team/bas.jpg'),
('Gino di Antonio','Attorney','diantonio@bj-advocatuur.nl','team/gino.jpg'),
]
BIOS = {
'John Wolfs': 'John Wolfs, entrepreneur at heart, is the founder of Wolfs Advocaten. He has been working as an attorney for almost 30 years. Before founding Wolfs Advocaten in 2003 he worked for leading firms in Washington DC and Rotterdam. His Maastricht roots, quality of life and love brought him back to Maastricht.\n\nJohn is known for his creativity, specialist sector knowledge and direct, pragmatic advice. He frequently lectures on transport law, international commercial law and insurance law. He advises entrepreneurs and insurers and assists them in international proceedings.\n\nOutside work, John enjoys squash and running. He has completed marathons in New York, San Francisco and Amsterdam.'
}
POSTS = [
('EU Abolishes 150 Euro Import Duty Exemption: New Flat-Rate Levy and Handling Fee for Low-Value E-Commerce Shipments','Abolition of import duty exemption: new European customs duty and handling fee for small e-commerce shipments from 2026.',date(2026,3,31)),
('The Dutch truck toll is coming','As of 1 July 2026, the truck charge will apply in the Netherlands. Learn about the consequences and practical application.',date(2025,8,26)),
('Employee liability for damages resulting from illegal transport activities','Truck driver summarily dismissed after smuggling 150 kg of tobacco. Must he also pay €24,000?',date(2025,8,20)),
('Declaration of controversy on cannabis experiment','What does the controversy around the cannabis experiment mean for entrepreneurs and investors?',date(2025,8,12)),
('Model residential lease renewed','A widely used model for residential leases has been updated. Read about the most important changes.',date(2025,8,5)),
('Returned goods relief','The Court of Justice recently ruled on circumstances in which importers may also qualify for VAT exemption.',date(2025,7,29)),
]
PAGES = [('terms-and-conditions','Terms & conditions'),('privacy-statement','Privacy statement'),('disclaimer','Disclaimer'),('cookie-policy','Cookie policy'),('vacancies','Vacancies'),('social-involvement','Social involvement')]

class Command(BaseCommand):
    help = 'Create editable starter content from the public site without overwriting existing edits.'
    def handle(self, *args, **options):
        SiteSettings.objects.get_or_create(pk=1, defaults={'hero_image':'site/hero.jpg','about_image':'site/about.jpg'})
        profile_file = Path(__file__).resolve().parents[2] / 'data' / 'profiles.json'
        profiles = {(kind, name): body for kind, name, body in json.loads(profile_file.read_text())} if profile_file.exists() else {}
        summaries = json.loads((Path(__file__).resolve().parents[2] / 'data' / 'practice_summaries.json').read_text())
        for i,(title,summary) in enumerate(AREAS,1):
            summary = summaries[i - 1]
            PracticeArea.objects.get_or_create(title=title,defaults={'summary':summary,'body':profiles.get(('area',title),summary),'image':f'practice/{i}.jpg','order':i})
        for i,(name,role,email,photo) in enumerate(TEAM,1):
            TeamMember.objects.get_or_create(name=name,defaults={'role':role,'email':email,'photo':photo,'biography':profiles.get(('team',name),BIOS.get(name,'')),'order':i, 'show_on_about': name in ('John Wolfs','Maurice van Efferink','Joost van den Akker','Menno van Term','Vera Ubaghs')})
        call_command('seed_about')
        archive = Path(__file__).resolve().parents[2] / 'data' / 'source_posts.json'
        if archive.exists():
            for item in json.loads(archive.read_text()):
                BlogPost.objects.get_or_create(title=item['title'], defaults={**item, 'published': True})
        else:
            for i,(title,excerpt,published_at) in enumerate(POSTS,1):
                BlogPost.objects.get_or_create(title=title,defaults={'excerpt':excerpt,'body':excerpt,'published_at':published_at,'published':True,'image':f'blog/{i}.jpg'})
        call_command('seed_practice_details')
        call_command('seed_remaining')
        call_command('seed_legal')
        for slug,title in PAGES:
            bodies = {
                'vacancies': 'Work with us\n\nWe are always on the lookout for new talent. If you speak Dutch, please contact us about opportunities for lawyers, student employees and interns at our Maastricht office. English-speaking candidates who think they could add value to our team are welcome to contact John Wolfs.',
                'social-involvement': 'Wolfs Advocaten values social responsibility and involvement. The firm supports local, regional and international social and cultural activities, including the Limburg Cancer Research Fund and the Alumni Council of the Faculty of Law at Maastricht University.',
                'cookie-policy': 'Wolfs Advocaten uses cookies on this website. A cookie is a small text file saved on your computer, tablet or smartphone when you visit a website. Cookies help the website remember preferences, such as your selected language, so future visits are easier. Cookies do not disclose your personal information, including your email address or telephone number.',
                'disclaimer': 'Information on this website is provided with care but does not constitute legal advice. For a legal question, please contact Wolfs Advocaten directly.',
            }
            ContentPage.objects.get_or_create(slug=slug,defaults={'title':title,'body':bodies.get(slug, f'Please open the original {title.lower()} document below.'),'document':f'documents/{slug}.pdf' if slug in ('terms-and-conditions','privacy-statement') else ''})
        self.stdout.write(self.style.SUCCESS('Starter content is ready.'))

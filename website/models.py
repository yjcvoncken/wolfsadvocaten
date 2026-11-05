from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class BilingualContent(models.Model):
    translations = models.JSONField(default=dict, blank=True)

    class Meta:
        abstract = True


class SiteSettings(BilingualContent):
    name = models.CharField(max_length=120, default='Wolfs Advocaten')
    tagline = models.CharField(max_length=200, default='Law. For all entrepreneurs.')
    intro = models.TextField(default='Proactive, realistic, international and fast.')
    phone = models.CharField(max_length=60, default='+31 (0)85 079 97 50')
    email = models.EmailField(default='info@wolfsadvocaten.nl')
    address = models.TextField(default='Wilhelminasingel 86\n6221 BL Maastricht\nThe Netherlands')
    visiting_address = models.TextField(default='Vijzelstraat 68\n1017 HL Amsterdam\nThe Netherlands')
    linkedin_url = models.URLField(blank=True, default='https://www.linkedin.com/company/wolfs-advocaten/posts/')
    hero_image = models.ImageField(max_length=500, upload_to='site/', blank=True)
    about_image = models.ImageField(max_length=500, upload_to='site/', blank=True)
    class Meta:
        verbose_name_plural = 'Site settings'
    def __str__(self): return self.name


class TeamMember(BilingualContent):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120)
    extra_line = models.CharField('Extra line below role', max_length=200, blank=True,
                                  help_text='Optional text shown below the role on team cards and the profile.')
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=60, blank=True)
    biography = models.TextField(blank=True)
    photo = models.ImageField(max_length=500, upload_to='team/', blank=True)
    order = models.PositiveIntegerField(default=0)
    published = models.BooleanField(default=True)
    show_on_home = models.BooleanField(default=True)
    show_on_about = models.BooleanField(default=True)
    class Meta:
        ordering = ['order', 'name']
    def get_absolute_url(self): return reverse('content_page', args=[slugify(self.name)])
    def __str__(self): return self.name


class PracticeArea(BilingualContent):
    title = models.CharField(max_length=160)
    slug = models.SlugField(unique=True, blank=True)
    summary = models.TextField()
    body = models.TextField(blank=True, help_text='Plain text; separate paragraphs with a blank line.')
    image = models.ImageField(max_length=500, upload_to='practice/', blank=True)
    detail_image = models.ImageField(max_length=500, upload_to='practice/', blank=True)
    secondary_image = models.ImageField(max_length=500, upload_to='practice/', blank=True)
    order = models.PositiveIntegerField(default=0)
    published = models.BooleanField(default=True)
    class Meta:
        ordering = ['order', 'title']
    def save(self, *args, **kwargs):
        if not self.slug: self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    def get_absolute_url(self): return reverse('practice_detail', args=[self.slug])
    def __str__(self): return self.title


class PracticeAreaSection(BilingualContent):
    area = models.ForeignKey(PracticeArea, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200)
    body = models.TextField()
    position = models.CharField(max_length=10, choices=(('intro', 'Beside main photo'),
                                                     ('detail', 'Below main photo')), default='intro')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'pk']

    def __str__(self):
        return self.title


class BlogPost(BilingualContent):
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    excerpt = models.TextField(blank=True)
    body = models.TextField(help_text='Plain text; separate paragraphs with a blank line.')
    image = models.ImageField(max_length=500, upload_to='blog/', blank=True)
    published_at = models.DateField()
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-published_at', '-id']
    def save(self, *args, **kwargs):
        if not self.slug: self.slug = slugify(self.title)[:250]
        super().save(*args, **kwargs)
    def get_absolute_url(self): return reverse('blog_detail', args=[self.slug])
    def __str__(self): return self.title


class ContentPage(BilingualContent):
    title = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    body = models.TextField(help_text='Plain text; separate paragraphs with a blank line.')
    lead = models.TextField(blank=True)
    image = models.ImageField(max_length=500, upload_to='pages/', blank=True)
    document_nl = models.FileField(max_length=500, upload_to='documents/', blank=True, verbose_name='Document (Dutch)')
    document = models.FileField(max_length=500, upload_to='documents/', blank=True, help_text='Optional PDF or document linked from this page.')
    published = models.BooleanField(default=True)
    def get_absolute_url(self): return reverse('content_page', args=[self.slug])
    def __str__(self): return self.title


class ContactSubmission(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=60, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    class Meta:
        ordering = ['-created_at']
    def __str__(self): return f'{self.first_name} {self.last_name} — {self.created_at:%Y-%m-%d}'


class AboutSection(BilingualContent):
    class Kind(models.TextChoices):
        INTRO = 'intro', 'Introduction'
        STORY = 'story', 'Story panel'
        NETWORK = 'network', 'Network'
        FOUNDER = 'founder', 'Founder biography'

    key = models.SlugField(unique=True, help_text='Stable identifier used by the page layout.')
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.STORY)
    title = models.CharField(max_length=160)
    lead = models.TextField(blank=True)
    body = models.TextField(blank=True, help_text='Separate paragraphs with a blank line.')
    image = models.ImageField(max_length=500, upload_to='about/', blank=True)
    link = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    published = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'About us section'
        verbose_name_plural = 'About us sections'

    def __str__(self):
        return self.title


class ImportantNetwork(AboutSection):
    class Meta:
        proxy = True
        verbose_name = 'Important network'
        verbose_name_plural = 'Important networks'


class ContentBlock(BilingualContent):
    page = models.ForeignKey(ContentPage, on_delete=models.CASCADE, related_name='blocks')
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    image = models.ImageField(max_length=500, upload_to='pages/', blank=True)
    link = models.CharField(max_length=300, blank=True, help_text='Local page path or external URL.')
    order = models.PositiveIntegerField(default=0)
    published = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class Vacancy(ContentBlock):
    class Meta:
        proxy = True
        verbose_name = 'Vacancy'
        verbose_name_plural = 'Vacancies'


class SitePhoto(models.Model):
    key = models.SlugField(unique=True)
    title = models.CharField(max_length=160)
    image = models.ImageField(max_length=500, upload_to='site/photos/', blank=True)

    class Meta:
        ordering = ['title']
        verbose_name = 'Photo'
        verbose_name_plural = 'Photos'

    def __str__(self):
        return self.title

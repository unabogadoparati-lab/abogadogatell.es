#!/usr/bin/env python3
"""
Generador de sitio estático para AbogadoGatell.es
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_package(package):
    """Instala un paquete usando pip si no está disponible"""
    try:
        __import__(package)
    except ImportError:
        print(f"Instalando {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])

def load_yaml(filepath):
    """Carga un archivo YAML"""
    try:
        import yaml
    except ImportError:
        install_package("pyyaml")
        import yaml
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_markdown(filepath):
    """Convierte un archivo Markdown a HTML"""
    try:
        import markdown
    except ImportError:
        install_package("markdown")
        import markdown
    
    with open(filepath, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    return markdown.markdown(md_content, extensions=['extra', 'codehilite', 'toc'])

def render_template(template_name, context):
    """Renderiza una plantilla Jinja2"""
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        install_package("jinja2")
        from jinja2 import Environment, FileSystemLoader
    
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template(template_name)
    return template.render(**context)

def parse_front_matter(content):
    """Extrae el front matter YAML y el contenido de un archivo Markdown"""
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            front_matter = parts[1]
            markdown_content = parts[2].strip()
            import yaml
            try:
                metadata = yaml.safe_load(front_matter)
            except:
                metadata = {}
            return metadata, markdown_content
    return {}, content

def main():
    print("Generando sitio web para AbogadoGatell.es...")
    
    # Directorios
    base_dir = Path(__file__).parent.parent
    content_dir = base_dir / 'content'
    templates_dir = base_dir / 'templates'
    output_dir = base_dir / 'output'
    static_dir = base_dir / 'static'
    
    # Limpiar directorio de salida
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()
    
    # Copiar assets estáticos
    if static_dir.exists():
        shutil.copytree(static_dir, output_dir / 'static')
    
    # Cargar configuración
    config_path = base_dir / 'config.yaml'
    config = load_yaml(config_path) if config_path.exists() else {}
    
    # Preparar contexto global
    site_context = {
        'site_title': config.get('title', 'AbogadoGatell.es'),
        'site_description': config.get('description', ''),
        'copyright': config.get('copyright', ''),
        'lang': config.get('language', 'es')
    }
    
    # Procesar contenido
    posts = []
    pages = []
    
    # Recopilar todos los archivos Markdown
    md_files = list(content_dir.rglob('*.md'))
    
    for md_file in md_files:
        # Ruta relativa desde content/
        rel_path = md_file.relative_to(content_dir)
        # Ruta de salida (cambiando .md por .html)
        output_path = output_dir / rel_path.with_suffix('.html')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Leer contenido
        with open(md_file, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        
        # Parsear front matter
        metadata, markdown_content = parse_front_matter(raw_content)
        
        # Convertir Markdown a HTML
        html_content = load_markdown(str(md_file))
        
        # Preparar contexto para la plantilla
        page_context = {
            **site_context,
            'title': metadata.get('title', 'Sin título'),
            'meta_description': metadata.get('excerpt', ''),
            'content': html_content,
            'post_title': metadata.get('title', 'Sin título'),
            'post_date': metadata.get('date', ''),
            'post_author': metadata.get('author', ''),
            'post_tags': metadata.get('tags', []),
            'post_excerpt': metadata.get('excerpt', '')
        }
        
        # Determinar qué plantilla usar
        if 'blog' in str(rel_path):
            template_name = 'post.html'
        else:
            template_name = 'page.html'  # Podemos crear una genérica o usar base
        
        # Si no existe la plantilla específica, usar base.html
        template_path = templates_dir / template_name
        if not template_path.exists():
            template_name = 'base.html'
        
        # Renderizar plantilla
        try:
            rendered_html = render_template(template_name, page_context)
        except Exception as e:
            print(f"Error al renderizar {md_file}: {e}")
            # Fallback a plantilla básica
            rendered_html = f"""
            <!DOCTYPE html>
            <html lang="{site_context['lang']}">
            <head>
                <meta charset="UTF-8">
                <title>{page_context['title']} - {site_context['site_title']}</title>
                <link rel="stylesheet" href="/static/css/style.css">
            </head>
            <body>
                <header>
                    <h1><a href="/">{site_context['site_title']}</a></h1>
                    <p>{site_context['site_description']}</p>
                </header>
                <main>
                    <article>
                        <h1>{page_context['title']}</h1>
                        <div>{html_content}</div>
                    </article>
                </main>
                <footer>
                    <p>{site_context['copyright']}</p>
                </footer>
            </body>
            </html>
            """
        
        # Escribir archivo de salida
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)
        
        # Recopilar información para el índice de blog
        if 'blog' in str(rel_path):
            posts.append({
                'title': metadata.get('title', 'Sin título'),
                'date': metadata.get('date', ''),
                'excerpt': metadata.get('excerpt', ''),
                'author': metadata.get('author', ''),
                'tags': metadata.get('tags', []),
                'url': str(rel_path.with_suffix('.html')).replace('\\', '/'),
                'output_path': output_path
            })
    
    # Generar índice de blog
    if posts:
        # Ordenar por fecha (más reciente primero)
        posts.sort(key=lambda x: x['date'], reverse=True)
        
        blog_context = {
            **site_context,
            'title': 'Blog',
            'meta_description': 'Publicaciones de AbogadoGatell.es sobre legal tech y inteligencia artificial',
            'content': '',  # Se remplazará en la plantilla
            'posts': posts
        }
        
        blog_html = render_template('blog_index.html', blog_context)
        
        blog_output = output_dir / 'blog' / 'index.html'
        blog_output.parent.mkdir(parents=True, exist_ok=True)
        with open(blog_output, 'w', encoding='utf-8') as f:
            f.write(blog_html)
    
    # Generar página de inicio (index.html)
    index_context = {
        **site_context,
        'title': 'Inicio',
        'meta_description': 'Despacho de abogado online que democratiza la justicia con herramientas de inteligencia artificial',
        'content': '''
        <section class="hero">
            <h2>Democratizando la justicia con IA</h2>
            <p>En AbogadoGatell.es utilizamos inteligencia artificial de vanguardia para hacer que los servicios legales sean más accesibles, eficientes y transparentes.</p>
            <a href="/blog/" class="btn">Leer nuestro blog</a>
        </section>
        
        <section class="services">
            <h2>Nuestros servicios</h2>
            <div class="services-grid">
                <div class="service">
                    <h3>Asesoría Legal IA</h3>
                    <p>Consultas legales asistidas por inteligencia artificial para respuestas rápidas y precisas.</p>
                </div>
                <div class="service">
                    <h3>Revisión de Documentos</h3>
                    <p>Análisis inteligente de contratos y documentos legales.</p>
                </div>
                <div class="service">
                    <h3>Gestión de Trámites</h3>
                    <p>Automatización de procesos legales y administrativos.</p>
                </div>
            </div>
        </section>
        '''
    }
    
    index_html = render_template('base.html', index_context)
    with open(output_dir / 'index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    print(f"Sitio generado exitosamente en {output_dir}")
    print(f"Total de archivos procesados: {len(md_files)}")
    print(f"Posts de blog: {len(posts)}")

if __name__ == '__main__':
    main()
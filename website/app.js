// Matrix rain effect — cascading characters in the page background
function createMatrixRain() {
    const canvas = document.getElementById('matrix-rain');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789{}[]<>/\\=+-*#$%@&_'.split('');
    const fontSize = 16;
    let columns = 0;
    let drops = [];

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        columns = Math.floor(canvas.width / fontSize);
        drops = new Array(columns).fill(0).map(() => Math.random() * -50);
    }

    function draw() {
        // Dark overlay — higher alpha = shorter, softer trails
        ctx.fillStyle = 'rgba(10, 10, 15, 0.18)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.font = `${fontSize}px "JetBrains Mono", monospace`;

        for (let i = 0; i < drops.length; i++) {
            const char = charset[Math.floor(Math.random() * charset.length)];
            const x = i * fontSize;
            const y = drops[i] * fontSize;

            // Leading character — dimmed slightly
            ctx.fillStyle = '#4db8cc';
            ctx.fillText(char, x, y);

            // Trailing accent one row up — even dimmer
            ctx.fillStyle = '#2a8fa3';
            ctx.fillText(char, x, y - fontSize);

            // Reset column at random once it falls off screen
            if (y > canvas.height && Math.random() > 0.975) {
                drops[i] = 0;
            }
            drops[i]++;
        }
    }

    resize();
    window.addEventListener('resize', resize);
    setInterval(draw, 55);
}

// Create floating particles
function createParticles() {
    const particlesContainer = document.getElementById('particles');
    const particleCount = 30;

    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 15 + 's';
        particle.style.animationDuration = (Math.random() * 10 + 10) + 's';
        particlesContainer.appendChild(particle);
    }
}

// Module-level projects store so modal functions can look up by ID
let _allProjects = [];

// Load projects from JSON file
async function loadProjects() {
    try {
        const response = await fetch('projects.json');
        const projects = await response.json();
        _allProjects = projects;
        renderProjects(projects);
        setupFilters(projects);
    } catch (error) {
        console.error('Error loading projects:', error);
        document.getElementById('projectsGrid').innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 4rem; color: var(--text-muted);">
                <p style="font-family: 'JetBrains Mono', monospace;">
                    No projects.json file found. Please create one to display your projects.
                </p>
            </div>
        `;
    }
}

// Render projects
function renderProjects(projects, filter = 'all') {
    const grid = document.getElementById('projectsGrid');
    
    const filteredProjects = filter === 'all' 
        ? projects 
        : projects.filter(p => p.category.includes(filter));

    if (filteredProjects.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 4rem; color: var(--text-muted);">
                <p>No projects found in this category.</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = filteredProjects.map(project => `
        <div class="project-card" data-categories="${project.category.join(' ')}">
            <div class="project-header">
                <h3>${project.title}</h3>
                <span class="project-date">${project.date}</span>
            </div>
            
            <p class="project-description">${project.description}</p>
            
            <div class="project-tags">
                ${project.tags.map(tag => {
                    let tagClass = 'tag';
                    if (tag.toLowerCase().includes('ml') || tag.toLowerCase().includes('model')) tagClass += ' ml';
                    if (tag.toLowerCase() === 'live') tagClass += ' live';
                    return `<span class="${tagClass}">${tag}</span>`;
                }).join('')}
            </div>
            
            ${project.metrics ? `
                <div class="project-metrics">
                    ${Object.entries(project.metrics).map(([key, value]) => `
                        <div class="metric">
                            <span class="metric-value">${value}</span>
                            <span class="metric-label">${key}</span>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
            
            <div class="project-links">
                ${project.blog_content_html ? `<a href="#" class="project-link" onclick="openBlogModal('${project.id}'); return false;">Read More</a>` : ''}
                ${project.github ? `<a href="${project.github}" class="project-link" target="_blank">Code</a>` : ''}
                ${project.demo_url ? `
                    <a href="#" class="project-link demo" onclick="openDemo('${project.id}', '${escapeQuotes(project.title)}', '${escapeQuotes(project.demo_description || '')}', '${project.demo_url}', ${project.category.includes('cv')}); return false;">
                        Live Demo
                    </a>
                ` : ''}
                ${project.article ? `<a href="${project.article}" class="project-link" target="_blank">Article</a>` : ''}
            </div>
        </div>
    `).join('');
}

// Helper function to escape quotes in strings
function escapeQuotes(str) {
    return str.replace(/'/g, "\\'").replace(/"/g, '\\"');
}

// Setup filter tabs
function setupFilters(projects) {
    const tabs = document.querySelectorAll('.filter-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            renderProjects(projects, tab.dataset.filter);
        });
    });
}

// Blog modal
function openBlogModal(projectId) {
    const project = _allProjects.find(p => p.id === projectId);
    if (!project) return;

    document.getElementById('blogModalTitle').textContent = project.title;
    document.getElementById('blogModalMeta').textContent =
        project.date + (project.category && project.category.length ? '  ·  ' + project.category.join(', ') : '');
    document.getElementById('blogModalTags').innerHTML = (project.tags || []).map(tag =>
        `<span class="tag">${tag}</span>`
    ).join('');
    document.getElementById('blogModalContent').innerHTML = project.blog_content_html || '';

    const links = [];
    if (project.github) {
        links.push(`<a href="${project.github}" class="project-link" target="_blank">View Code on GitHub</a>`);
    }
    if (project.demo_url) {
        const isCV = (project.category || []).includes('cv');
        links.push(`<a href="#" class="project-link demo" onclick="closeBlogModal(); openDemo('${project.id}', '${escapeQuotes(project.title)}', '${escapeQuotes(project.demo_description || '')}', '${project.demo_url}', ${isCV}); return false;">Try Live Demo</a>`);
    }
    document.getElementById('blogModalLinks').innerHTML = links.join('');

    document.getElementById('blogModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeBlogModal() {
    document.getElementById('blogModal').classList.remove('active');
    document.body.style.overflow = '';
}

// Demo modal
let currentDemoUrl = '';
let currentIsCV = false;

function openDemo(projectId, title, description, demoUrl, isCV = false) {
    document.getElementById('modalTitle').textContent = title + ' - Live Demo';
    document.getElementById('modalDescription').textContent = description;
    document.getElementById('demoOutput').textContent = 'Awaiting prediction...';
    document.getElementById('demoModal').classList.add('active');
    
    currentDemoUrl = demoUrl;
    currentIsCV = isCV;
    
    // Setup input based on model type
    const inputContainer = document.getElementById('demoInputContainer');
    
    if (isCV) {
        // Computer Vision - use file input
        inputContainer.innerHTML = `
            <label style="display: block; margin-bottom: 0.5rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">
                UPLOAD IMAGE
            </label>
            <input 
                type="file" 
                id="demoInput" 
                accept="image/*"
                class="demo-input" 
                style="padding: 0.75rem; cursor: pointer;">
            <div id="imagePreview" style="margin-top: 1rem; text-align: center;"></div>
        `;
    } else {
        // NLP/ML - use text input
        inputContainer.innerHTML = `
            <label style="display: block; margin-bottom: 0.5rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">
                INPUT DATA
            </label>
            <textarea 
                id="demoInput" 
                class="demo-input" 
                rows="4" 
                placeholder="Enter your input here..."></textarea>
        `;
    }
    
    // Add change listener for image preview
    if (isCV) {
        document.getElementById('demoInput').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    document.getElementById('imagePreview').innerHTML = `
                        <img src="${event.target.result}" style="max-width: 100%; max-height: 300px; border: 1px solid var(--border); border-radius: 4px;">
                    `;
                };
                reader.readAsDataURL(file);
            }
        });
    }
}

function closeModal() {
    document.getElementById('demoModal').classList.remove('active');
}

// Run ML demo
async function runDemo() {
    const output = document.getElementById('demoOutput');
    
    if (currentIsCV) {
        // Handle image input
        const fileInput = document.getElementById('demoInput');
        const file = fileInput.files[0];
        
        if (!file) {
            output.textContent = 'Error: Please select an image file';
            return;
        }
        
        output.innerHTML = '<div class="loading"></div> Running inference...';
        
        try {
            // Convert image to base64
            const reader = new FileReader();
            reader.onload = async function(e) {
                const base64Image = e.target.result.split(',')[1];
                
                // Call Lambda with image
                const response = await fetch(currentDemoUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        image: base64Image,
                        filename: file.name
                    })
                });
                
                const result = await response.json();
                output.textContent = JSON.stringify(result, null, 2);
            };
            reader.readAsDataURL(file);
        } catch (error) {
            output.textContent = `Error: ${error.message}\n\nNote: Make sure your AWS Lambda endpoint is configured and accessible.`;
        }
    } else {
        // Handle text input
        const input = document.getElementById('demoInput').value;
        
        if (!input.trim()) {
            output.textContent = 'Error: Please provide input data';
            return;
        }
        
        output.innerHTML = '<div class="loading"></div> Running inference...';
        
        try {
            const response = await fetch(currentDemoUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ input: input })
            });
            
            const result = await response.json();
            output.textContent = JSON.stringify(result, null, 2);
        } catch (error) {
            output.textContent = `Error: ${error.message}\n\nNote: Make sure your AWS Lambda endpoint is configured and accessible.`;
        }
    }
}

// Close modals on outside click or Escape key
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('demoModal')?.addEventListener('click', function(e) {
        if (e.target === this) closeModal();
    });
    document.getElementById('blogModal')?.addEventListener('click', function(e) {
        if (e.target === this) closeBlogModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeBlogModal();
            closeModal();
        }
    });
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    createMatrixRain();
    createParticles();
    loadProjects();
});

// Smooth scrolling
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

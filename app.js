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

// Load projects from JSON file
async function loadProjects() {
    try {
        const response = await fetch('projects.json');
        const projects = await response.json();
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
                ${project.github ? `<a href="${project.github}" class="project-link" target="_blank">Code</a>` : ''}
                ${project.demo_url ? `
                    <a href="#" class="project-link demo" onclick="openDemo('${project.id}', '${project.title}', '${project.demo_description || ''}', '${project.demo_url}'); return false;">
                        Live Demo
                    </a>
                ` : ''}
                ${project.article ? `<a href="${project.article}" class="project-link" target="_blank">Article</a>` : ''}
            </div>
        </div>
    `).join('');
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

// Modal functions
let currentDemoUrl = '';

function openDemo(projectId, title, description, demoUrl) {
    document.getElementById('modalTitle').textContent = title + ' - Live Demo';
    document.getElementById('modalDescription').textContent = description;
    document.getElementById('demoInput').value = '';
    document.getElementById('demoOutput').textContent = 'Awaiting prediction...';
    document.getElementById('demoModal').classList.add('active');
    currentDemoUrl = demoUrl;
}

function closeModal() {
    document.getElementById('demoModal').classList.remove('active');
}

// Run ML demo
async function runDemo() {
    const input = document.getElementById('demoInput').value;
    const output = document.getElementById('demoOutput');

    if (!input.trim()) {
        output.textContent = 'Error: Please provide input data';
        return;
    }

    output.innerHTML = '<div class="loading"></div> Running inference...';

    try {
        // Call AWS Lambda endpoint
        const response = await fetch(currentDemoUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ input: input })
        });

        const result = await response.json();
        
        // Format the output
        output.textContent = JSON.stringify(result, null, 2);
    } catch (error) {
        output.textContent = `Error: ${error.message}\n\nNote: Make sure your AWS Lambda endpoint is configured and accessible.`;
    }
}

// Close modal on outside click
document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('demoModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal();
            }
        });
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
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

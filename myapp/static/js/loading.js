document.addEventListener('DOMContentLoaded', function() {
    // Loading overlay functionality
    const loadingOverlay = document.querySelector('.loading-overlay');
    
    // Show loading overlay when navigation starts
    window.addEventListener('beforeunload', function() {
        loadingOverlay.classList.add('active');
    });

    // Show loading during AJAX requests
    let activeRequests = 0;
    const originalFetch = window.fetch;
    window.fetch = function() {
        activeRequests++;
        loadingOverlay.classList.add('active');
        
        return originalFetch.apply(this, arguments)
            .finally(function() {
                activeRequests--;
                if (activeRequests === 0) {
                    loadingOverlay.classList.remove('active');
                }
            });
    };

    // Show loading overlay during form submissions
    document.addEventListener('submit', function() {
        loadingOverlay.classList.add('active');
    });

    // Hide loading overlay when page is fully loaded
    window.addEventListener('load', function() {
        loadingOverlay.classList.remove('active');
    });

    // Add loading for dynamic content loading
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                loadingOverlay.classList.add('active');
                setTimeout(() => {
                    loadingOverlay.classList.remove('active');
                }, 500); // Minimum display time
            }
        });
    });

    // Observe elements with data-observe attribute for lazy loading
    document.querySelectorAll('[data-observe]').forEach(el => observer.observe(el));
}); 
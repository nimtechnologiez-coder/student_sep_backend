
    async function fetchAndSwap(url) {
      try {
        const tbody = document.querySelector('#notifsTable tbody');
        if (tbody) tbody.style.opacity = '0.4';
        
        window.history.pushState({}, '', url);
        const response = await fetch(url);
        const htmlText = await response.text();
        const doc = new DOMParser().parseFromString(htmlText, 'text/html');
        
        const newTbody = doc.querySelector('#notifsTable tbody');
        if (newTbody && tbody) tbody.innerHTML = newTbody.innerHTML;
        
        const currentPagination = document.querySelector('.pagination-row');
        const newPagination = doc.querySelector('.pagination-row');
        if (currentPagination && newPagination) currentPagination.innerHTML = newPagination.innerHTML;
        
        const currentTabs = document.querySelector('.filter-tabs-row');
        const newTabs = doc.querySelector('.filter-tabs-row');
        if (currentTabs && newTabs) currentTabs.innerHTML = newTabs.innerHTML;

        const currentKpis = document.querySelector('.kpi-cards-grid');
        const newKpis = doc.querySelector('.kpi-cards-grid');
        if (currentKpis && newKpis) currentKpis.innerHTML = newKpis.innerHTML;
        
        if (tbody) tbody.style.opacity = '1';
      } catch (err) {
        console.error(err);
        window.location.href = url;
      }
    }

    function updateFilters(params) {
      const urlParams = new URLSearchParams(window.location.search);
      for (const [key, value] of Object.entries(params)) {
        if (value) urlParams.set(key, value);
        else urlParams.delete(key);
      }
      urlParams.delete('page');
      fetchAndSwap('?' + urlParams.toString());
    }

    function filterByTab(btn, category) {
      document.querySelectorAll('.pill-tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      updateFilters({category: category});
    }

    function goToPage(page) {
      const urlParams = new URLSearchParams(window.location.search);
      urlParams.set('page', page);
      fetchAndSwap('?' + urlParams.toString());
    }

    const searchInput = document.getElementById('notifSearchInput');
    if (searchInput) {
      searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') updateFilters({q: this.value});
      });
    }

    const categoryFilter = document.getElementById('notifCategorySelect');
    if (categoryFilter) {
      categoryFilter.addEventListener('change', function() {
        updateFilters({category: this.value});
      });
    }

    const targetFilter = document.getElementById('notifTargetSelect');
    if (targetFilter) {
      targetFilter.addEventListener('change', function() {
        updateFilters({target: this.value});
      });
    }

    const statusFilter = document.getElementById('notifStatusSelect');
    if (statusFilter) {
      statusFilter.addEventListener('change', function() {
        updateFilters({status: this.value});
      });
    }

    // Close modal when clicking on overlay background
    document.getElementById('addBroadcastModal').addEventListener('click', function(e) {
      if (e.target === this) {
        this.classList.remove('active');
      }
    });
  

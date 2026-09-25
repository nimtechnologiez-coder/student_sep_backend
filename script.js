
    function updateFilters(params) {
      const urlParams = new URLSearchParams(window.location.search);
      for (const [key, value] of Object.entries(params)) {
        if (value) urlParams.set(key, value);
        else urlParams.delete(key);
      }
      urlParams.delete('page');
      window.location.search = urlParams.toString();
    }

    document.getElementById('batchSearchInput').addEventListener('keypress', function(e) {
      if (e.key === 'Enter') updateFilters({q: this.value});
    });

    const statusFilter = document.getElementById('batchStatusFilter');
    if (statusFilter) {
      statusFilter.addEventListener('change', function() {
        updateFilters({status: this.value});
      });
    }

    function goToPage(page) {
      const urlParams = new URLSearchParams(window.location.search);
      urlParams.set('page', page);
      window.location.search = urlParams.toString();
    }
  

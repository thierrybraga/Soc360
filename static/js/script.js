document.addEventListener("DOMContentLoaded", () => {
  // Inicializa cada módulo somente se os elementos necessários estiverem presentes
  if (document.getElementById("vulnData")) {
    initVulnerabilityDashboard();
  }
  if (document.getElementById("severityChart")) {
    initAnalyticsPage();
  }
});

/* =========================
   MÓDULO: Dashboard de Vulnerabilidades
   ========================= */
function initVulnerabilityDashboard() {
  // --- Helpers ---
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    if (isNaN(date)) return dateString;
    const day = String(date.getDate()).padStart(2, "0");
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const year = String(date.getFullYear()).slice(-2);
    return `${day}/${month}/${year}`;
  };

  const generateCSV = () => {
    const headers = ["CVE ID", "Descrição", "Data de Publicação", "Severidade", "Fornecedor", "CVSS Score"];
    const rows = filteredVulnerabilities.map(vuln => [
      vuln["CVE ID"],
      vuln["Description"],
      formatDate(vuln["Published Date"]),
      vuln["Severity"],
      vuln["Vendor"],
      vuln["CVSS Score"]
    ]);
    const csvContent = "data:text/csv;charset=utf-8," +
      [headers, ...rows].map(row => row.join(",")).join("\n");
    const link = document.createElement("a");
    link.href = encodeURI(csvContent);
    link.download = "vulnerabilities_report.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Essa função utiliza updateDashboard que deve estar definida em outro módulo, se necessário
  const fetchCveData = async (vendor = '') => {
    try {
      const response = await fetch(`/api/vulnerabilities?vendor=${vendor}`);
      if (!response.ok) {
        throw new Error(`Erro na requisição: ${response.statusText}`);
      }
      const data = await response.json();
      updateDashboard(data);
    } catch (error) {
      console.error("Erro ao carregar dados da API:", error);
      alert("Erro ao carregar dados. Tente novamente mais tarde.");
    }
  };

  const getSeverityColor = (severity) => {
    if (!severity) return "";
    switch (severity.toLowerCase()) {
      case "critical":
      case "high":
        return "text-danger";
      case "medium":
        return "text-warning";
      case "low":
        return "text-success";
      default:
        return "";
    }
  };

  const sortByDate = (data) =>
    data.sort((a, b) => new Date(b["Published Date"]) - new Date(a["Published Date"]));

  // --- Seleção de Elementos e Dados Iniciais ---
  const vulnerabilityDataEl = document.getElementById("vulnData");
  const vulnerabilities = JSON.parse(vulnerabilityDataEl.textContent);
  const itemsPerPage = 10;
  let currentPage = 1;
  let filteredVulnerabilities = [...vulnerabilities];

  const tableBody = document.getElementById("vulnTableBody");
  const paginationEl = document.getElementById("pagination");
  const generateReportBtn = document.getElementById("generateReportBtn");
  const yearFilterEl = document.getElementById("year");
  const vendorFilterEl = document.getElementById("vendor");
  const severityFilterEl = document.getElementById("severity");
  const clearFiltersBtn = document.getElementById("clearFiltersBtn");
  const loadingEl = document.getElementById("loading");

  // --- Funções de Construção da Tabela ---
  const createVulnerabilityRow = (vuln) => {
    const row = document.createElement("tr");

    // Data formatada e cor de severidade
    const formattedDate = formatDate(vuln["Published Date"]);
    const severityColorClass = getSeverityColor(vuln["Severity"]);

// Processa o link de referência de forma segura
let refLink = "#";
if (vuln["reference_links"]) {
  try {
    let parsedLinks;
    const refData = vuln["reference_links"].trim();
    // Se o dado começar com [ assume que é JSON, caso contrário, usa split
    if (refData.startsWith("[")) {
      parsedLinks = JSON.parse(refData.replace(/'/g, '"'));
    } else {
      parsedLinks = refData.split(",");
    }
    refLink = (Array.isArray(parsedLinks) && parsedLinks.length > 0) ? parsedLinks[0].trim() : "#";
  } catch (error) {
    console.error("Erro ao processar link de referência:", error);
  }
}


    // CVE ID com link
    const cveCell = document.createElement("td");
    const cveLink = document.createElement("a");
    cveLink.href = refLink;
    cveLink.target = "_blank";
    cveLink.textContent = vuln["CVE ID"];
    cveLink.setAttribute("aria-label", `Link para ${vuln["CVE ID"]}`);
    cveCell.appendChild(cveLink);
    row.appendChild(cveCell);

    // Descrição
    const descriptionCell = document.createElement("td");
    descriptionCell.textContent = vuln["Description"];
    row.appendChild(descriptionCell);

    // Data de Publicação
    const dateCell = document.createElement("td");
    dateCell.textContent = formattedDate;
    row.appendChild(dateCell);

    // Severidade com classe de cor
    const severityCell = document.createElement("td");
    severityCell.textContent = vuln["Severity"];
    severityCell.classList.add(severityColorClass);
    row.appendChild(severityCell);

    // Fornecedor
    const vendorCell = document.createElement("td");
    vendorCell.textContent = vuln["Vendor"];
    row.appendChild(vendorCell);

    // CVSS Score
    const cvssCell = document.createElement("td");
    cvssCell.textContent = vuln["CVSS Score"];
    row.appendChild(cvssCell);

    // Botão de relatório
    const reportCell = document.createElement("td");
    const reportButton = document.createElement("button");
    reportButton.className = "btn btn-success btn-sm";
    reportButton.innerHTML = `<i class="fas fa-file-alt"></i> Gerar Relatório`;
    reportButton.setAttribute("aria-label", `Gerar relatório para ${vuln["CVE ID"]}`);
    reportButton.addEventListener("click", () => downloadReport(vuln["CVE ID"]));
    reportCell.appendChild(reportButton);
    row.appendChild(reportCell);

    return row;
  };

  const displayTable = () => {
    tableBody.innerHTML = "";
    const startIdx = (currentPage - 1) * itemsPerPage;
    const pageData = filteredVulnerabilities.slice(startIdx, startIdx + itemsPerPage);

    if (!pageData.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 7;
      cell.className = "text-center";
      cell.textContent = "Nenhuma vulnerabilidade encontrada.";
      row.appendChild(cell);
      tableBody.appendChild(row);
    } else {
      pageData.forEach(vuln => tableBody.appendChild(createVulnerabilityRow(vuln)));
    }
    updatePagination();
  };

  // --- Funções de Paginação ---
  const updatePagination = () => {
    paginationEl.innerHTML = "";
    const totalPages = Math.ceil(filteredVulnerabilities.length / itemsPerPage);
    if (totalPages <= 1) return;

    createPaginationButton("Primeira", 1, totalPages, "angle-double-left");
    createPaginationButton("Anterior", currentPage - 1, totalPages, "chevron-left");

    const maxPageButtons = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxPageButtons / 2));
    let endPage = startPage + maxPageButtons - 1;
    if (endPage > totalPages) {
      endPage = totalPages;
      startPage = Math.max(1, endPage - maxPageButtons + 1);
    }

    if (startPage > 1) {
      const ellipsisLi = document.createElement("li");
      ellipsisLi.className = "page-item disabled";
      ellipsisLi.innerHTML = `<span class="page-link">...</span>`;
      paginationEl.appendChild(ellipsisLi);
    }

    for (let i = startPage; i <= endPage; i++) {
      createPaginationButton(i, i, totalPages);
    }

    if (endPage < totalPages) {
      const ellipsisLi = document.createElement("li");
      ellipsisLi.className = "page-item disabled";
      ellipsisLi.innerHTML = `<span class="page-link">...</span>`;
      paginationEl.appendChild(ellipsisLi);
    }

    createPaginationButton("Próxima", currentPage + 1, totalPages, "chevron-right");
    createPaginationButton("Última", totalPages, totalPages, "angle-double-right");
  };

  const createPaginationButton = (label, pageNum, totalPages, icon) => {
    const li = document.createElement("li");
    const isDisabled = pageNum === currentPage || pageNum < 1 || pageNum > totalPages;
    li.className = `page-item${isDisabled ? " disabled" : ""}`;
    li.innerHTML = icon
      ? `<a class="page-link" href="#" aria-label="${label}"><i class="fas fa-${icon}"></i></a>`
      : `<a class="page-link" href="#" aria-label="Página ${label}">${label}</a>`;
    li.addEventListener("click", (e) => {
      e.preventDefault();
      if (!isDisabled) {
        currentPage = pageNum;
        displayTable();
      }
    });
    paginationEl.appendChild(li);
  };

  // --- Funções de Filtro ---
  const applyFilters = () => {
    const year = yearFilterEl.value;
    const vendor = vendorFilterEl.value;
    const severity = severityFilterEl.value;

    filteredVulnerabilities = vulnerabilities.filter(vuln =>
      (!year || vuln["Published Date"].includes(year)) &&
      (!vendor || vuln["Vendor"] === vendor) &&
      (!severity || vuln["Severity"].toLowerCase() === severity.toLowerCase())
    );

    filteredVulnerabilities = sortByDate(filteredVulnerabilities);
    generateReportBtn.disabled = !(year && vendor && severity);
    currentPage = 1;
    displayTable();
  };

  const clearFilters = () => {
    yearFilterEl.value = "";
    vendorFilterEl.value = "";
    severityFilterEl.value = "";
    filteredVulnerabilities = sortByDate([...vulnerabilities]);
    generateReportBtn.disabled = true;
    currentPage = 1;
    displayTable();
  };

  // --- Função de Download de Relatório ---
  window.downloadReport = (cve_id) => {
    showLoading();
    fetch(`/generate_report?cve_id=${cve_id}`)
      .then(response => {
        if (!response.ok) {
          alert("Erro ao gerar o relatório.");
          throw new Error("Erro na requisição");
        }
        return response.blob();
      })
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `relatorio_vulnerabilidade_${cve_id}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      })
      .catch(error => console.error("Download report error:", error))
      .finally(() => hideLoading());
  };

  // --- Funções de Loading ---
  const showLoading = () => { loadingEl.style.display = "block"; };
  const hideLoading = () => { loadingEl.style.display = "none"; };

  // --- Eventos ---
  yearFilterEl.addEventListener("change", applyFilters);
  vendorFilterEl.addEventListener("change", applyFilters);
  severityFilterEl.addEventListener("change", applyFilters);
  clearFiltersBtn.addEventListener("click", clearFilters);
  generateReportBtn.addEventListener("click", generateCSV);

  // --- Inicialização ---
  filteredVulnerabilities = sortByDate(filteredVulnerabilities);
  displayTable();
}

/* =========================
   MÓDULO: Página de Analytics
   ========================= */
function initAnalyticsPage() {
  // Seleciona os elementos do DOM
  const applyFiltersButton = document.getElementById("apply-filters");
  const vendorFilterEl = document.getElementById("vendor-filter");
  const vendorTableBody = document.getElementById("vendor-table-body");
  const originalButtonContent = applyFiltersButton.innerHTML;
  let severityChart, cvssScoreChart, cveHistoryChart;
  let chartsInitialized = false;

  // --- Funções de Loading para o botão ---
  const showLoading = () => {
    applyFiltersButton.disabled = true;
    applyFiltersButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Carregando...';
  };
  const hideLoading = () => {
    applyFiltersButton.disabled = false;
    applyFiltersButton.innerHTML = originalButtonContent;
  };

  // --- Atualiza o dashboard de vendors ---
  const updateDashboard = (data) => {
    vendorTableBody.innerHTML = data.topVendors
      .map(vendor => `<tr><td>${vendor.name}</td><td>${vendor.quantity}</td></tr>`)
      .join("");
    vendorFilterEl.innerHTML =
      '<option value="">Todos</option>' +
      data.vendors.map(vendor => `<option value="${vendor}">${vendor}</option>`).join("");
  };

  // --- Inicializa os gráficos com Chart.js ---
  const initializeCharts = (data) => {
    const ctxSeverity = document.getElementById('severityChart').getContext('2d');
    severityChart = new Chart(ctxSeverity, {
      type: 'pie',
      data: {
        labels: ["Critical", "High", "Medium", "Low"],
        datasets: [{
          data: [
            data.severity.critical || 0,
            data.severity.high || 0,
            data.severity.medium || 0,
            data.severity.low || 0
          ],
          backgroundColor: ['#dc3545', '#fd7e14', '#ffc107', '#28a745']
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom' } }
      }
    });

    const ctxCvss = document.getElementById('cvssScoreChart').getContext('2d');
    cvssScoreChart = new Chart(ctxCvss, {
      type: 'bar',
      data: {
        labels: ["0-2", "3-4", "5-6", "7-8", "9-10"],
        datasets: [{
          label: 'Quantidade',
          data: data.cvssScoreDistribution,
          backgroundColor: '#007bff'
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } }
      }
    });

    const ctxHistory = document.getElementById('cveHistoryChart').getContext('2d');
    cveHistoryChart = new Chart(ctxHistory, {
      type: 'line',
      data: {
        labels: data.cveHistoryLabels,
        datasets: [{
          label: 'CVEs',
          data: data.cveHistoryData,
          fill: false,
          borderColor: '#17a2b8',
          tension: 0.1
        }]
      },
      options: {
        responsive: true,
        scales: { y: { beginAtZero: true } }
      }
    });
  };

  // --- Atualiza os gráficos com novos dados ---
  const updateCharts = (data) => {
    severityChart.data.datasets[0].data = [
      data.severity.critical || 0,
      data.severity.high || 0,
      data.severity.medium || 0,
      data.severity.low || 0
    ];
    severityChart.update();

    cvssScoreChart.data.datasets[0].data = data.cvssScoreDistribution;
    cvssScoreChart.update();

    cveHistoryChart.data.labels = data.cveHistoryLabels;
    cveHistoryChart.data.datasets[0].data = data.cveHistoryData;
    cveHistoryChart.update();
  };

  // --- Busca dados da API e atualiza a interface ---
  const fetchDashboardData = async (vendor = "") => {
    showLoading();
    const url = vendor ? `/api/cves?vendor=${encodeURIComponent(vendor)}` : "/api/cves";
    try {
      const response = await fetch(url);
      const data = await response.json();
      updateDashboard(data);
      if (!chartsInitialized) {
        initializeCharts(data);
        chartsInitialized = true;
      } else {
        updateCharts(data);
      }
    } catch (error) {
      console.error("Erro ao carregar dados da API:", error);
      alert("Erro ao carregar dados da API. Por favor, tente novamente.");
    } finally {
      hideLoading();
    }
  };

  // --- Eventos ---
  applyFiltersButton.addEventListener("click", () => {
    fetchDashboardData(vendorFilterEl.value);
  });

  window.addEventListener("load", () => {
    fetchDashboardData();
  });
}


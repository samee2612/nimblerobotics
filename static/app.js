let exceptionData;
let activePlan;
let selectedOrderId = 'NB-48291';

const $ = (selector) => document.querySelector(selector);
const money = (value) => `$${Number(value).toFixed(2)}`;

async function loadException() {
  const response = await fetch(`/api/exception?order_id=${encodeURIComponent(selectedOrderId)}`);
  exceptionData = await response.json();
  const { order, orders } = exceptionData;
  selectedOrderId = order.id;
  $('#order-select').innerHTML = orders.map((item) => `<option value="${item.id}" ${item.id === order.id ? 'selected' : ''}>${item.id} · ${item.customer} · ${item.risk}</option>`).join('');
  $('#queue-count').textContent = orders.length;
  $('#order-id').textContent = order.id;
  $('#order-summary').innerHTML = [
    ['CUSTOMER', order.customer], ['DESTINATION', order.destination],
    ['ORDER VALUE', money(order.value)], ['PROMISED', order.promised_delivery]
  ].map(([label, value]) => `<div class="summary-item"><span>${label}</span><b>${value}</b></div>`).join('');
  $('#risk-reason').textContent = order.risk_reason;
}

function planName(plan) {
  return `${plan.source_warehouse} → ${plan.carrier_service}`;
}

async function generatePlan() {
  $('#plan-button').disabled = true;
  $('#plan-button').innerHTML = 'Generating… <span>◌</span>';
  $('#loading').classList.remove('hidden');
  $('#result').classList.add('hidden');
  await new Promise((resolve) => setTimeout(resolve, 900));
  try {
    const response = await fetch(`/api/plan?order_id=${encodeURIComponent(selectedOrderId)}`, { method: 'POST' });
    if (!response.ok) throw new Error('Could not generate plan');
    const result = await response.json();
    activePlan = result.plan;
    $('#plan-title').textContent = planName(result.plan);
    $('#customer-impact').textContent = result.plan.customer_impact;
    $('#plan-cost').textContent = money(result.plan.incremental_cost);
    $('#confidence').textContent = `${result.plan.confidence} confidence`;
    $('#rationale').textContent = result.plan.rationale;
    $('#source-badge').textContent = result.source === 'gemini' ? 'Gemini structured output' : 'Local fallback';
    $('#ai-status').textContent = result.ai_status;
    $('#decision-context').textContent = result.decision_context;
    $('#checks').innerHTML = result.validation.checks.map((check) => `<div class="check"><span class="check-icon">${check.passed ? '✓' : '!'}</span><div><b>${check.name}</b><span>${check.detail}</span></div></div>`).join('');
    $('#rejection').textContent = result.rejected_validation.rejection_reason;
    $('#rejected-plan').textContent = JSON.stringify(result.rejected_candidate, null, 2);
    $('#recovery-options').innerHTML = result.recovery_options.map((option) => `<article class="option ${option.status}"><div class="option-top"><b>${option.title}</b><span>${option.status}</span></div><p>${option.detail}</p><strong>${money(option.incremental_cost)}</strong></article>`).join('');
    $('#result').classList.remove('hidden');
    $('#result').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    alert('Something went wrong. Please reload and try again.');
  } finally {
    $('#loading').classList.add('hidden');
    $('#plan-button').disabled = false;
    $('#plan-button').innerHTML = 'Generate recovery plan <span>→</span>';
  }
}

async function approvePlan() {
  $('#approve-button').disabled = true;
  $('#approve-button').textContent = 'Approving…';
  const response = await fetch('/api/approve', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ order_id: selectedOrderId, plan: activePlan })
  });
  if (!response.ok) return alert('The plan did not pass validation.');
  const audit = await response.json();
  $('#audit-title').textContent = `${audit.decision} approved`;
  $('#audit-detail').textContent = `${audit.id} · ${audit.approved_by} · ${audit.approved_at} · ${money(audit.incremental_cost)} incremental cost`;
  $('#audit').classList.remove('hidden');
  $('#audit').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

$('#plan-button').addEventListener('click', generatePlan);
$('#approve-button').addEventListener('click', approvePlan);
$('#order-select').addEventListener('change', async (event) => {
  selectedOrderId = event.target.value;
  $('#result').classList.add('hidden');
  $('#audit').classList.add('hidden');
  await loadException();
});
$('#reset-button').addEventListener('click', () => { $('#audit').classList.add('hidden'); $('#result').classList.add('hidden'); window.scrollTo({top: 0, behavior: 'smooth'}); });
loadException();

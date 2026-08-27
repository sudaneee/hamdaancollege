/* =========================================================
   APPLY.JS — client-side step navigation for the (single-form,
   real server POST) admission application page.
   ========================================================= */

const applyState = { step: 1, totalSteps: 6 };

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('applyForm');
  if (!form) return;

  renderStepper();

  document.querySelectorAll('[data-next]').forEach(btn => btn.addEventListener('click', () => goStep(applyState.step + 1)));
  document.querySelectorAll('[data-prev]').forEach(btn => btn.addEventListener('click', () => goStep(applyState.step - 1)));

  document.querySelectorAll('.upload-box').forEach(box => {
    const input = box.querySelector('input[type="file"]');
    if (!input) return;
    box.addEventListener('click', e => { if (e.target !== input) input.click(); });
    input.addEventListener('change', () => {
      if (input.files && input.files.length) {
        box.classList.add('uploaded');
        box.querySelector('.upload-status').textContent = input.files[0].name;
        box.querySelector('i').className = 'fa-solid fa-circle-check';
      }
    });
  });

  // If the server re-rendered the form with validation errors, jump to the
  // first step that actually has an error so the user isn't stuck on the
  // last step.
  const firstErrorStep = document.querySelector('.form-step [data-field-error]')?.closest('.form-step');
  if (firstErrorStep) {
    goStep(Number(firstErrorStep.dataset.step));
  }

  form.addEventListener('submit', () => {
    const btn = document.getElementById('submitAppBtn');
    btn?.classList.add('btn-loading');
  });
});

function validateStep(step) {
  const stepEl = document.querySelector(`.form-step[data-step="${step}"]`);
  if (!stepEl) return true;
  let valid = true;
  stepEl.querySelectorAll('[required]').forEach(input => {
    const wrap = input.closest('.field');
    if (!input.value || !input.value.trim()) {
      wrap?.classList.add('error');
      valid = false;
    } else {
      wrap?.classList.remove('error');
    }
  });
  return valid;
}

function goStep(step) {
  if (step > applyState.step && !validateStep(applyState.step)) return;
  if (step < 1 || step > applyState.totalSteps) return;
  if (step === applyState.totalSteps) buildReviewSummary();
  applyState.step = step;
  document.querySelectorAll('.form-step').forEach(s => s.classList.toggle('active', Number(s.dataset.step) === step));
  renderStepper();
  document.getElementById('applyFormCard')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderStepper() {
  const labels = ['Personal', 'Guardian', 'Programme', 'Education', 'Documents', 'Review & Submit'];
  const el = document.getElementById('applyStepper');
  if (!el) return;
  el.innerHTML = labels.map((lab, i) => {
    const n = i + 1;
    const state = n < applyState.step ? 'done' : n === applyState.step ? 'active' : '';
    return `<div class="stepper-item ${state}">
      <div class="stepper-circle">${n < applyState.step ? '<i class="fa-solid fa-check"></i>' : n}</div>
      <span>${lab}</span>
    </div>`;
  }).join('');
}

function buildReviewSummary() {
  const val = id => document.getElementById(id);
  const text = id => (val(id)?.value) || '—';
  const selectedText = id => { const el = val(id); return el ? (el.options[el.selectedIndex]?.text || '—') : '—'; };
  const summary = document.getElementById('reviewSummary');
  if (!summary) return;
  summary.innerHTML = `
    <div class="review-block"><h5>Personal Information</h5>
      <div class="review-row"><span>Name</span><span>${text('id_surname')} ${text('id_first_name')} ${text('id_middle_name')}</span></div>
      <div class="review-row"><span>Date of Birth</span><span>${text('id_date_of_birth')}</span></div>
      <div class="review-row"><span>Gender</span><span>${selectedText('id_gender')}</span></div>
      <div class="review-row"><span>Phone</span><span>${text('id_phone')}</span></div>
      <div class="review-row"><span>Email</span><span>${text('id_email')}</span></div>
      <div class="review-row"><span>State / LGA</span><span>${selectedText('id_state_of_origin')} / ${text('id_lga')}</span></div>
    </div>
    <div class="review-block"><h5>Guardian / Next of Kin</h5>
      <div class="review-row"><span>Name</span><span>${text('id_guardian_name')}</span></div>
      <div class="review-row"><span>Relationship</span><span>${selectedText('id_guardian_relationship')}</span></div>
      <div class="review-row"><span>Phone</span><span>${text('id_guardian_phone')}</span></div>
    </div>
    <div class="review-block"><h5>Programme</h5>
      <div class="review-row"><span>Programme</span><span>${selectedText('id_programme')}</span></div>
    </div>
    <div class="review-block"><h5>Educational Background</h5>
      <div class="review-row"><span>School Attended</span><span>${text('id_previous_school')}</span></div>
      <div class="review-row"><span>Qualification</span><span>${text('id_qualification_obtained')} (${text('id_qualification_year')})</span></div>
    </div>`;
}

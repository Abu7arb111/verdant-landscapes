document.addEventListener('DOMContentLoaded', () => {

  // ==========================================
  // 1. Header Scroll Effect
  // ==========================================
  const header = document.getElementById('site-header');
  
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
  });

  // ==========================================
  // 2. Mobile Navigation Toggle
  // ==========================================
  const menuToggle = document.getElementById('menu-toggle-btn');
  const navMenu = document.getElementById('nav-menu');
  const navLinks = navMenu.querySelectorAll('a');

  menuToggle.addEventListener('click', () => {
    const isExpanded = menuToggle.getAttribute('aria-expanded') === 'true';
    menuToggle.setAttribute('aria-expanded', !isExpanded);
    navMenu.classList.toggle('active');
  });

  // Close menu when clicking a link
  navLinks.forEach(link => {
    link.addEventListener('click', () => {
      menuToggle.setAttribute('aria-expanded', 'false');
      navMenu.classList.remove('active');
      
      // Update active link styling
      navLinks.forEach(l => l.classList.remove('active'));
      link.classList.add('active');
    });
  });

  // Close menu when clicking outside
  document.addEventListener('click', (e) => {
    if (!header.contains(e.target) && navMenu.classList.contains('active')) {
      menuToggle.setAttribute('aria-expanded', 'false');
      navMenu.classList.remove('active');
    }
  });

  // ==========================================
  // 3. Portfolio Filtering
  // ==========================================
  const filterButtons = document.querySelectorAll('.filter-btn');
  const portfolioItems = document.querySelectorAll('.portfolio-item');

  filterButtons.forEach(button => {
    button.addEventListener('click', () => {
      // Remove active class from all buttons
      filterButtons.forEach(btn => btn.classList.remove('active'));
      button.classList.add('active');

      const filterValue = button.getAttribute('data-filter');

      portfolioItems.forEach(item => {
        const itemCategory = item.getAttribute('data-category');
        
        // Dynamic animation transition
        item.style.opacity = '0';
        item.style.transform = 'scale(0.8)';
        
        setTimeout(() => {
          if (filterValue === 'all' || itemCategory === filterValue) {
            item.style.display = 'block';
            setTimeout(() => {
              item.style.opacity = '1';
              item.style.transform = 'scale(1)';
            }, 50);
          } else {
            item.style.display = 'none';
          }
        }, 300);
      });
    });
  });

  // ==========================================
  // 4. Interactive Multi-Select & Photo Estimator
  // ==========================================
  let currentStep = 1;
  const totalSteps = 3;

  // File Upload State
  let uploadedFileName = null;
  let uploadedFileData = null;

  // DOM Elements
  const prevBtn = document.getElementById('btn-wizard-prev');
  const nextBtn = document.getElementById('btn-wizard-next');
  const submitBtn = document.getElementById('btn-wizard-submit');
  
  const stepDots = document.querySelectorAll('.progress-step');
  const progressBarFill = document.getElementById('progress-bar-fill');
  const wizardSteps = document.querySelectorAll('.wizard-step');

  const leadForm = document.getElementById('lead-form');
  const successModal = document.getElementById('quote-success-modal');
  const closeModalBtn = document.getElementById('btn-modal-close');

  const photoInput = document.getElementById('yard-photo-input');
  const uploadZone = document.getElementById('photo-upload-zone');
  const previewContainer = document.getElementById('upload-preview-container');
  const previewImg = document.getElementById('uploaded-preview-img');
  const removePreviewBtn = document.getElementById('btn-remove-preview');

  // Handle service checkbox clicks (Step 1)
  const serviceCheckboxes = document.querySelectorAll('.checkbox-card');
  serviceCheckboxes.forEach(card => {
    card.addEventListener('click', () => {
      card.classList.toggle('selected');
    });
  });

  // File Upload and Drag & Drop Listeners (Step 2)
  function handleFileSelection(file) {
    if (!file) return;

    if (!file.type.match('image.*')) {
      alert('Please upload a valid image file (PNG, JPG, or WEBP).');
      return;
    }

    uploadedFileName = file.name;
    
    const reader = new FileReader();
    reader.onload = (e) => {
      uploadedFileData = e.target.result;
      previewImg.src = uploadedFileData;
      uploadZone.style.display = 'none';
      previewContainer.style.display = 'block';
    };
    reader.readAsDataURL(file);
  }

  photoInput.addEventListener('change', (e) => {
    handleFileSelection(e.target.files[0]);
  });

  // Drag over highlights
  ['dragenter', 'dragover'].forEach(eventName => {
    uploadZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      uploadZone.classList.add('dragover');
    }, false);
  });

  ['dragleave', 'dragend', 'drop'].forEach(eventName => {
    uploadZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      uploadZone.classList.remove('dragover');
    }, false);
  });

  uploadZone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const file = dt.files[0];
    handleFileSelection(file);
  });

  removePreviewBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    
    photoInput.value = '';
    previewImg.src = '';
    previewContainer.style.display = 'none';
    uploadZone.style.display = 'block';
    
    uploadedFileName = null;
    uploadedFileData = null;
  });

  // Wizard navigation logic
  function goToStep(step) {
    if (step < 1 || step > totalSteps) return;

    wizardSteps.forEach(s => s.classList.remove('active'));
    document.getElementById(`wizard-step-${step}`).classList.add('active');

    stepDots.forEach(dot => {
      const dotStep = parseInt(dot.getAttribute('data-step'));
      if (dotStep < step) {
        dot.className = 'progress-step completed';
      } else if (dotStep === step) {
        dot.className = 'progress-step active';
      } else {
        dot.className = 'progress-step';
      }
    });

    const progressPercent = ((step - 1) / (totalSteps - 1)) * 100;
    progressBarFill.style.width = `${progressPercent}%`;

    currentStep = step;
    
    if (currentStep === 1) {
      prevBtn.style.display = 'none';
      nextBtn.style.display = 'block';
      submitBtn.style.display = 'none';
    } else if (currentStep === totalSteps) {
      prevBtn.style.display = 'block';
      nextBtn.style.display = 'none';
      submitBtn.style.display = 'block';
    } else {
      prevBtn.style.display = 'block';
      nextBtn.style.display = 'block';
      submitBtn.style.display = 'none';
    }
  }

  nextBtn.addEventListener('click', () => {
    if (currentStep === 1) {
      const selectedCount = document.querySelectorAll('.checkbox-card.selected').length;
      if (selectedCount === 0) {
        alert('Please select at least one landscaping service.');
        return;
      }
    }
    
    if (currentStep === 2) {
      if (!uploadedFileName) {
        alert('Please upload a photo of your yard to continue.');
        return;
      }
    }
    
    goToStep(currentStep + 1);
  });

  prevBtn.addEventListener('click', () => {
    goToStep(currentStep - 1);
  });

  // Lead Submission Handler
  submitBtn.addEventListener('click', (e) => {
    const isFormValid = leadForm.checkValidity();
    if (!isFormValid) {
      leadForm.reportValidity();
      return;
    }

    e.preventDefault();

    const name = document.getElementById('lead-name').value;
    const phone = document.getElementById('lead-phone').value;
    const message = document.getElementById('lead-message').value;
    
    const refId = 'LVB-' + Math.floor(1000 + Math.random() * 9000);

    const selectedCards = document.querySelectorAll('.checkbox-card.selected');
    const selectedServicesList = Array.from(selectedCards).map(card => 
      card.querySelector('h5').textContent
    );
    const servicesSummary = selectedServicesList.join(', ');

    const quoteLead = {
      refId,
      name,
      phone,
      message,
      services: selectedServicesList,
      photoName: uploadedFileName,
      photoContentSimulated: uploadedFileData ? 'Simulated base64 visual' : null,
      submittedAt: new Date().toISOString()
    };

    let existingLeads = JSON.parse(localStorage.getItem('vcl_leads')) || [];
    existingLeads.push(quoteLead);
    localStorage.setItem('vcl_leads', JSON.stringify(existingLeads));

    // Calculate simulated AI Yard & Inch Measurement based on selected services
    const baseSqFt = 350 + (selectedCards.length * 150);
    const sqYd = (baseSqFt / 9).toFixed(1);
    const perimeterInches = Math.round(Math.sqrt(baseSqFt) * 4 * 12);
    
    const aiMeasureStr = `${baseSqFt} sq ft / ${sqYd} sq yd (${perimeterInches} in perimeter)`;

    // Determine equipment list based on services
    let toolsList = ['Plate Compactor', 'Sod Cutter'];
    if (servicesSummary.toLowerCase().includes('patio') || servicesSummary.toLowerCase().includes('wall') || servicesSummary.toLowerCase().includes('hardscape')) {
      toolsList.push('Paver Tile Saw', 'Mini-Excavator');
    }
    if (servicesSummary.toLowerCase().includes('drainage') || servicesSummary.toLowerCase().includes('renovation')) {
      toolsList.push('Tractor Trencher', 'Laser Leveler');
    }
    const toolsStr = toolsList.join(', ');

    const crewStr = `VA Beach Specialist Crew #${Math.floor(1 + Math.random() * 5)} (Near Town Center)`;

    // Populate Modal Summary Details
    document.getElementById('summary-ref-id').textContent = refId;
    document.getElementById('summary-service').textContent = servicesSummary;
    document.getElementById('summary-photo-name').textContent = uploadedFileName || 'yard_preview.png';
    document.getElementById('summary-phone').textContent = phone;

    const measureEl = document.getElementById('summary-ai-measure');
    if (measureEl) measureEl.textContent = aiMeasureStr;

    const toolsEl = document.getElementById('summary-ai-tools');
    if (toolsEl) toolsEl.textContent = toolsStr;

    const crewEl = document.getElementById('summary-ai-crew');
    if (crewEl) crewEl.textContent = crewStr;

    successModal.classList.add('active');

    leadForm.reset();
    
    photoInput.value = '';
    previewImg.src = '';
    previewContainer.style.display = 'none';
    uploadZone.style.display = 'block';
    uploadedFileName = null;
    uploadedFileData = null;

    serviceCheckboxes.forEach(c => {
      if (c.getAttribute('data-value') === 'design') c.classList.add('selected');
      else c.classList.remove('selected');
    });

    goToStep(1);
  });

  closeModalBtn.addEventListener('click', () => {
    successModal.classList.remove('active');
  });

  successModal.addEventListener('click', (e) => {
    if (e.target === successModal) {
      successModal.classList.remove('active');
    }
  });


  // ==========================================
  // 5. Interactive Appointment Booking Calendar
  // ==========================================
  const monthTitle = document.getElementById('month-title');
  const calendarCells = document.getElementById('calendar-grid-cells');
  const prevMonthBtn = document.getElementById('prev-month-btn');
  const nextMonthBtn = document.getElementById('next-month-btn');

  const slotsContainer = document.getElementById('slots-container');
  const noDateMessage = document.getElementById('no-date-selected-message');
  const selectedDateLabel = document.getElementById('selected-date-label');
  const timeSlotsGrid = document.getElementById('time-slots-grid');

  const apptFormBox = document.getElementById('appointment-form-box');
  const bookingSummaryText = document.getElementById('booking-summary-text');
  const appointmentForm = document.getElementById('appointment-submit-form');
  const successApptCard = document.getElementById('booking-success-card');
  const bookAnotherBtn = document.getElementById('btn-book-another');

  const months = [
    'January', 'February', 'March', 'April', 'May', 'June', 
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  let calendarYear = 2026;
  let calendarMonth = 5; // June (0-indexed)
  
  const todayDateObj = new Date(2026, 5, 14);

  let selectedDayNum = null;
  let selectedSlotTime = null;

  function renderCalendar() {
    const elementsToRemove = calendarCells.querySelectorAll('.calendar-day');
    elementsToRemove.forEach(el => el.remove());

    monthTitle.textContent = `${months[calendarMonth]} ${calendarYear}`;

    const firstDayIndex = new Date(calendarYear, calendarMonth, 1).getDay();
    const daysInMonth = new Date(calendarYear, calendarMonth + 1, 0).getDate();

    for (let i = 0; i < firstDayIndex; i++) {
      const emptyCell = document.createElement('span');
      emptyCell.className = 'calendar-day empty';
      calendarCells.appendChild(emptyCell);
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const dayCell = document.createElement('span');
      dayCell.className = 'calendar-day';
      dayCell.textContent = day;

      const dateOfCell = new Date(calendarYear, calendarMonth, day);

      if (dateOfCell < todayDateObj) {
        dayCell.classList.add('disabled');
      }

      if (calendarYear === 2026 && calendarMonth === 5 && day === 14) {
        dayCell.classList.add('today');
      }

      if (selectedDayNum === day && calendarMonth === 5 && calendarYear === 2026) {
        dayCell.classList.add('selected');
      }

      dayCell.addEventListener('click', () => {
        if (dayCell.classList.contains('disabled')) return;
        
        calendarCells.querySelectorAll('.calendar-day').forEach(cell => {
          cell.classList.remove('selected');
        });

        dayCell.classList.add('selected');
        selectedDayNum = day;
        
        showAvailableSlots(day);
      });

      calendarCells.appendChild(dayCell);
    }
  }

  prevMonthBtn.addEventListener('click', () => {
    if (calendarYear === 2026 && calendarMonth === 5) return;
    
    calendarMonth--;
    if (calendarMonth < 0) {
      calendarMonth = 11;
      calendarYear--;
    }
    renderCalendar();
  });

  nextMonthBtn.addEventListener('click', () => {
    calendarMonth++;
    if (calendarMonth > 11) {
      calendarMonth = 0;
      calendarYear++;
    }
    renderCalendar();
  });

  function showAvailableSlots(day) {
    const formattedDate = `${months[calendarMonth]} ${day}, ${calendarYear}`;
    selectedDateLabel.textContent = formattedDate;

    selectedSlotTime = null;
    apptFormBox.classList.remove('active');
    successApptCard.style.display = 'none';

    noDateMessage.style.display = 'none';
    slotsContainer.style.display = 'block';

    const availableSlots = ['9:00 AM', '10:30 AM', '1:00 PM', '2:30 PM', '4:30 PM'];
    timeSlotsGrid.innerHTML = '';

    availableSlots.forEach(time => {
      const slotBtn = document.createElement('button');
      slotBtn.className = 'slot-btn';
      slotBtn.textContent = time;

      const isBooked = (day + time.length) % 3 === 0;
      if (isBooked) {
        slotBtn.classList.add('booked');
      } else {
        slotBtn.addEventListener('click', () => {
          timeSlotsGrid.querySelectorAll('.slot-btn').forEach(btn => {
            btn.classList.remove('selected');
          });

          slotBtn.classList.add('selected');
          selectedSlotTime = time;
          
          bookingSummaryText.textContent = `Selected: ${months[calendarMonth]} ${day}, ${calendarYear} at ${time}`;
          apptFormBox.classList.add('active');
        });
      }

      timeSlotsGrid.appendChild(slotBtn);
    });
  }

  appointmentForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const name = document.getElementById('appt-name').value;
    const phone = document.getElementById('appt-phone').value;
    const service = document.getElementById('appt-service').value;
    const apptRef = 'APT-' + Math.floor(1000 + Math.random() * 9000);
    const dateStr = `${months[calendarMonth]} ${selectedDayNum}, ${calendarYear}`;

    const appointment = {
      apptRef,
      name,
      phone,
      service,
      date: dateStr,
      time: selectedSlotTime,
      createdAt: new Date().toISOString()
    };

    let existingAppts = JSON.parse(localStorage.getItem('vcl_appointments')) || [];
    existingAppts.push(appointment);
    localStorage.setItem('vcl_appointments', JSON.stringify(existingAppts));

    document.getElementById('success-appt-details').textContent = `${dateStr} at ${selectedSlotTime} (${service})`;
    document.getElementById('success-appt-ref').textContent = '#' + apptRef;

    slotsContainer.style.display = 'none';
    apptFormBox.classList.remove('active');
    successApptCard.style.display = 'block';
  });

  bookAnotherBtn.addEventListener('click', () => {
    selectedDayNum = null;
    selectedSlotTime = null;
    appointmentForm.reset();
    successApptCard.style.display = 'none';
    noDateMessage.style.display = 'block';
    renderCalendar();
  });

  renderCalendar();


  // ==========================================
  // 6. Floating AI Chat Assistant (Sandy)
  // ==========================================
  const chatTriggerBtn = document.getElementById('floating-chat-btn');
  const chatWindow = document.getElementById('chat-bot-window');
  const chatCloseBtn = document.getElementById('btn-chat-close');
  const chatMessagesLog = document.getElementById('chat-messages-log');
  const chatInputMsg = document.getElementById('chat-input-msg');
  const chatSendBtn = document.getElementById('btn-chat-send');
  const chatQuickChips = document.getElementById('chat-quick-reply-chips');
  const chatStartTimestamp = document.getElementById('chat-message-time-start');

  // Format initial message timestamp
  if (chatStartTimestamp) {
    const now = new Date();
    let hours = now.getHours();
    let minutes = now.getMinutes();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12; // Hour '0' should be '12'
    minutes = minutes < 10 ? '0' + minutes : minutes;
    chatStartTimestamp.textContent = `${hours}:${minutes} ${ampm}`;
  }

  // Toggle Chat Panel
  chatTriggerBtn.addEventListener('click', () => {
    chatWindow.classList.toggle('active');
    if (chatWindow.classList.contains('active')) {
      chatInputMsg.focus();
      scrollChatToBottom();
    }
  });

  chatCloseBtn.addEventListener('click', () => {
    chatWindow.classList.remove('active');
  });

  // Scroll messages to bottom helper
  function scrollChatToBottom() {
    chatMessagesLog.scrollTop = chatMessagesLog.scrollHeight;
  }

  // Append user or bot message bubble
  function appendMessage(text, isUser = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-message ${isUser ? 'user' : 'bot'}`;

    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'chat-bubble';
    bubbleDiv.innerHTML = text; // innerHTML allows bolding/links in bot replies

    const timeSpan = document.createElement('span');
    timeSpan.className = 'chat-message-time';
    
    const now = new Date();
    let hours = now.getHours();
    let minutes = now.getMinutes();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12;
    minutes = minutes < 10 ? '0' + minutes : minutes;
    timeSpan.textContent = `${hours}:${minutes} ${ampm}`;

    msgDiv.appendChild(bubbleDiv);
    msgDiv.appendChild(timeSpan);
    chatMessagesLog.appendChild(msgDiv);
    scrollChatToBottom();
  }

  // Show dynamic typing indicator bubble
  function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.id = 'chat-typing-indicator';
    
    for (let i = 0; i < 3; i++) {
      const dot = document.createElement('div');
      dot.className = 'typing-dot';
      indicator.appendChild(dot);
    }

    chatMessagesLog.appendChild(indicator);
    scrollChatToBottom();
    return indicator;
  }

  // Conversation script mappings
  function getBotResponse(userMsg) {
    const query = userMsg.toLowerCase().trim();

    if (query.includes('pricing') || query.includes('package') || query.includes('tier') || query.includes('how much')) {
      return `We offer 3 transparent, upfront service packages:<br><br><strong>1. Essential Care ($1,499+):</strong> Lawn edging, Bermuda/Tall Fescue sod, flowerbeds & mulch.<br><strong>2. Full Transformation ($4,999+):</strong> [Most Popular] 3D design blueprint, 350 sq ft paver patio, path lighting & French drain.<br><strong>3. Executive Hardscape ($9,999+):</strong> Outdoor kitchen or fire pit, retaining walls, pool decks & cedar privacy fencing.<br><br>Check out our <strong>Pricing Packages</strong> section on the homepage for full details!`;
    }

    if (query.includes('before') || query.includes('after') || query.includes('transform') || query.includes('gallery')) {
      return `Check out our interactive **Visual Transformations** section! You can drag the interactive slider left and right to see real Virginia Beach homes before and after our hardscape and landscaping upgrades!`;
    }

    if (query.includes('team') || query.includes('about') || query.includes('who are you') || query.includes('owner')) {
      return `Verdant Landscapes was founded in 2011 by <strong>Marcus Holloway</strong> (Lead Landscape Architect) and <strong>Sarah Kensington</strong> (Master Horticultural Specialist). We are a Virginia Class A Licensed & Insured contractor with over 15 years of service in Hampton Roads!`;
    }

    if (query.includes('warranty') || query.includes('guarantee') || query.includes('licensed')) {
      return `We stand behind our work 100%! We provide:<br>• <strong>1-Year Workmanship Warranty</strong> on all patios, pavers, and retaining walls.<br>• <strong>30-Day Health Guarantee</strong> on all new sod, trees, and plantings.<br>• We are a fully **Virginia Class A Licensed & Insured** contractor.`;
    }

    if (query.includes('measure') || query.includes('inch') || query.includes('yard') || query.includes('dimension') || query.includes('square')) {
      return `📐 <strong>AI Computer-Vision Measurement:</strong><br>When you upload a photo of your front or backyard, our AI measures your lawn surface area, slope, and perimeter accurately down to the <strong>yard and inch</strong> (±0.5 in precision)!`;
    }

    if (query.includes('tool') || query.includes('equipment') || query.includes('machinery') || query.includes('machine') || query.includes('excavator')) {
      return `🚜 <strong>AI Equipment & Tools Prescribed:</strong><br>Our AI evaluates your yard photo to prescribe the exact heavy machinery and specialized tools required for the project (e.g. Kubota mini-excavators, sod cutters, wet paver tile saws, plate compactors, and trenchers).`;
    }

    if (query.includes('who to call') || query.includes('who call') || query.includes('call next') || query.includes('crew') || query.includes('specialist') || query.includes('contractor')) {
      return `📞 <strong>Local Virginia Beach Specialists Assigned:</strong><br>Our system automatically identifies who to call next to you! It matches your specific project requirements with certified local specialists in Virginia Beach (master stone masons, irrigation plumbers, and turf specialists).`;
    }

    if (query.includes('estimate') || query.includes('quote') || query.includes('photo') || query.includes('cost') || query.includes('price')) {
      return `To get a custom estimate for your project:<br><br>1. Scroll to the <strong>AI Instant Photo Estimator</strong> section on the homepage.<br>2. Select all the services you are interested in (multi-select).<br>3. Upload or drag-and-drop a photo of your lawn or yard in Step 2.<br>4. Enter your contact details in Step 3.<br><br>Our AI will measure your yard by the inch, prescribe required tools & machinery, and call you at <strong>(540) 257-6053</strong> with the complete quote!`;
    }
    
    if (query.includes('service') || query.includes('offer') || query.includes('do you do') || query.includes('list')) {
      return `We provide a comprehensive list of premium residential services in Virginia Beach:<br><br><strong>• Design & Makeover:</strong> Landscape design, complete front yard makeovers, backyard renovations, pool landscaping.<br><strong>• Hardscaping:</strong> Patios, stone pavers, retaining walls, privacy fencing.<br><strong>• Yard Works:</strong> Sod installation, French drainage, flower bed construction, tree planting, shrub planting, mulching, decorative stone, and smart landscape lighting.<br><br>We can estimate any combination of these!`;
    }

    if (query.includes('drainage') || query.includes('french drain') || query.includes('water') || query.includes('pooling') || query.includes('mud')) {
      return `Standing water and drainage leaks are very common in Virginia Beach coastal properties. We design and install custom **French drains, catch basins, surface grading, and gutter extensions** to direct water away from your home.<br><br>If you upload a photo of your pooling areas in our **Estimator tool**, our engineers will evaluate the grade and include drainage details in your quote request!`;
    }

    if (query.includes('appointment') || query.includes('schedule') || query.includes('book') || query.includes('consult') || query.includes('free consult')) {
      return `You can book a free on-site design consultation directly on our calendar! Scroll down to the **Design Consultation** section, pick an available date on the calendar, select a convenient time slot, and fill out your details. Your appointment will be confirmed instantly.`;
    }

    if (query.includes('sod') || query.includes('grass') || query.includes('lawn') || query.includes('turf')) {
      return `Our sod installation process is thorough:<br>1. Complete clearing of weeds, old thatch, and debris.<br>2. Grading and tilling in fresh nutrient-rich topsoil.<br>3. Laying premium local sod rolls (tall fescue/bermuda).<br>4. Rolling and outlining watering schedules.<br><br>Upload a photo of your existing lawn in our Estimator to get started!`;
    }

    if (query.includes('pay') || query.includes('card') || query.includes('visa') || query.includes('mastercard') || query.includes('amex') || query.includes('apple pay') || query.includes('checkout')) {
      return `Yes, we accept major credit cards for your convenience, including **Visa, Mastercard, and American Express**, as well as **Apple Pay** and bank transfers. We secure deposits before launching on-site works.`;
    }

    if (query.includes('phone') || query.includes('call') || query.includes('contact') || query.includes('number')) {
      return `You can call us directly at our toll-free office line: <strong>(540) 257-6053</strong>.<br><br>We are active Monday through Saturday, 8:00 AM to 6:00 PM.`;
    }

    if (query.includes('hello') || query.includes('hi') || query.includes('hey') || query.includes('yo')) {
      return `Hello! How can I assist you with your Virginia Beach landscaping project today? 🌊`;
    }

    // Default reply
    return `That sounds interesting! To give you the best answer, I recommend:<br><br>1. Uploading a photo of your yard in our <strong>Instant Photo Estimator</strong> section for a custom analysis.<br>2. Scheduling a free on-site visit in our **Design Consultation** calendar section.<br>3. Or calling us directly at <strong>(540) 257-6053</strong> to chat with our lead designer.`;
  }

  // Handle Query Posting
  function processUserMessage(msgText) {
    if (!msgText.trim()) return;

    // Post User Bubble
    appendMessage(msgText, true);
    chatInputMsg.value = '';

    // Show Typing indicator
    const indicator = showTypingIndicator();

    // Mock bot reply with typing delay
    setTimeout(() => {
      // Remove typing bubble
      if (indicator && indicator.parentNode) {
        indicator.parentNode.removeChild(indicator);
      }
      
      const botReply = getBotResponse(msgText);
      appendMessage(botReply, false);
    }, 1000);
  }

  // Listeners for Chat Inputs
  chatSendBtn.addEventListener('click', () => {
    processUserMessage(chatInputMsg.value);
  });

  chatInputMsg.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      processUserMessage(chatInputMsg.value);
    }
  });

  // Prompt Chips Click listener
  chatQuickChips.addEventListener('click', (e) => {
    const chip = e.target.closest('.chat-chip-btn');
    if (chip) {
      const query = chip.getAttribute('data-query');
      processUserMessage(query);
    }
  });

  // ==========================================
  // 7. Before & After Drag Comparison Slider
  // ==========================================
  const baContainer = document.getElementById('ba-comparison-slider');
  const baBeforeLayer = document.getElementById('ba-before-layer');
  const baHandle = document.getElementById('ba-slider-handle');

  if (baContainer && baBeforeLayer && baHandle) {
    let isDraggingBA = false;

    function setSliderPosition(xPos) {
      const rect = baContainer.getBoundingClientRect();
      let offsetX = xPos - rect.left;
      if (offsetX < 0) offsetX = 0;
      if (offsetX > rect.width) offsetX = rect.width;

      const percentage = (offsetX / rect.width) * 100;
      baBeforeLayer.style.width = `${percentage}%`;
      baHandle.style.left = `${percentage}%`;
    }

    baContainer.addEventListener('mousedown', (e) => {
      isDraggingBA = true;
      setSliderPosition(e.clientX);
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDraggingBA) return;
      setSliderPosition(e.clientX);
    });

    window.addEventListener('mouseup', () => {
      isDraggingBA = false;
    });

    baContainer.addEventListener('touchstart', (e) => {
      isDraggingBA = true;
      if (e.touches.length > 0) {
        setSliderPosition(e.touches[0].clientX);
      }
    });

    window.addEventListener('touchmove', (e) => {
      if (!isDraggingBA) return;
      if (e.touches.length > 0) {
        setSliderPosition(e.touches[0].clientX);
      }
    });

    window.addEventListener('touchend', () => {
      isDraggingBA = false;
    });
  }

  // ==========================================
  // 8. FAQ Accordion Interactivity
  // ==========================================
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach((item) => {
    const questionBtn = item.querySelector('.faq-question');
    if (questionBtn) {
      questionBtn.addEventListener('click', () => {
        const isActive = item.classList.contains('active');
        faqItems.forEach((other) => {
          other.classList.remove('active');
          const otherBtn = other.querySelector('.faq-question');
          if (otherBtn) otherBtn.setAttribute('aria-expanded', 'false');
        });
        if (!isActive) {
          item.classList.add('active');
          questionBtn.setAttribute('aria-expanded', 'true');
        }
      });
    }
  });

  // ==========================================
  // 9. Pricing Package Buttons Interactivity
  // ==========================================
  const selectPackageBtns = document.querySelectorAll('.select-package-btn');
  selectPackageBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const pkgName = btn.getAttribute('data-package');
      if (pkgName) {
        if (chatWindow && !chatWindow.classList.contains('active')) {
          chatWindow.classList.add('active');
        }
        processUserMessage(`I'm interested in the ${pkgName} package!`);
      }
    });
  });

});


/* ═══════════════════════════════════════════════════════════
   i18n.js — Thai / English language switcher
   Uses data-i18n, data-i18n-placeholder, data-i18n-aria attrs
   ═══════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  const STORAGE_KEY  = 'pf-lang';
  const DEFAULT_LANG = 'th';

  // ─────────────────────────────────────────────
  // TRANSLATIONS
  // ─────────────────────────────────────────────
  const T = {
    th: {
      /* ── Navbar ── */
      'nav.home'          : 'หน้าแรก',
      'nav.lost'          : 'ประกาศสัตว์หาย',
      'nav.found'         : 'ประกาศสัตว์พบ',
      'nav.map'           : '🗺️ แผนที่',
      'nav.ai_search'     : '🔍 AI ค้นหา',
      'nav.products'      : 'สินค้า',
      'nav.blog'          : 'บทความ',
      'nav.login'         : 'เข้าสู่ระบบ',
      'nav.profile'       : '👤 โปรไฟล์ ▾',
      'nav.my_profile'    : '⚙️ โปรไฟล์ของฉัน',
      'nav.my_posts'      : '📢 ประกาศของฉัน',
      'nav.report_lost'   : '➕ แจ้งสัตว์หาย',
      'nav.report_found'  : '🐾 แจ้งสัตว์ที่พบ',
      'nav.logout'        : '🚪 ออกจากระบบ',

      /* ── Footer ── */
      'ft.tagline'        : 'เว็บไซต์ช่วยตามหาสัตว์เลี้ยงหาย ใช้ AI จับคู่รูปภาพ พาน้องกลับบ้านอย่างปลอดภัย',
      'ft.browse'         : 'ค้นหา',
      'ft.lost'           : 'ประกาศสัตว์หาย',
      'ft.found'          : 'ประกาศสัตว์พบ',
      'ft.map'            : 'แผนที่',
      'ft.ai_search'      : 'ค้นหาด้วย AI',
      'ft.community'      : 'ชุมชน',
      'ft.blog'           : 'บทความ',
      'ft.products'       : 'สินค้าแนะนำ',
      'ft.report_lost'    : 'แจ้งสัตว์หาย',
      'ft.report_found'   : 'แจ้งสัตว์ที่พบ',
      'ft.login'          : 'เข้าสู่ระบบ',
      'ft.signup'         : 'สมัครสมาชิก',

      /* ── Lost / Found list ── */
      'list.hero_lost'       : 'ประกาศสัตว์เลี้ยงหาย',
      'list.hero_found'      : 'ประกาศสัตว์เลี้ยงที่พบ',
      'list.hero_sub'        : 'ด้านล่างนี้',
      'list.btn_report_lost' : '+ ลงประกาศสัตว์หาย',
      'list.btn_report_found': '+ ลงประกาศสัตว์ที่พบ',
      'list.btn_view_found'  : 'ดูสัตว์พบ',
      'list.btn_view_lost'   : 'ดูสัตว์หาย',
      'list.search_text'     : 'ค้นหาด้วยคำ (ชื่อ, สายพันธุ์, สถานที่)',
      'list.search_ai'       : 'ค้นหาด้วยรูปภาพ (AI)',
      'list.search_btn'      : 'ค้นหา',
      'list.hint_text_lost'  : 'กรองจากประกาศสัตว์หายโดยตรง',
      'list.hint_text_found' : 'กรองจากประกาศสัตว์ที่พบโดยตรง',
      'list.hint_ai'         : 'อัปโหลดรูปเพื่อให้ AI ค้นหาประกาศที่ใกล้เคียง',
      'list.search_label'    : 'ผลการค้นหา',
      'list.found_dash'      : '— พบ',
      'list.count_pre'       : 'มีประกาศอยู่',
      'list.result_unit'     : 'รายการ',
      'list.clear'           : 'ล้างการค้นหา',
      'list.badge_pet'       : 'สัตว์เลี้ยง',
      'list.badge_lost'      : 'หาย',
      'list.badge_found'     : 'พบ',
      'list.label_gender'    : 'เพศ',
      'list.label_age'       : 'อายุ',
      'list.empty_lost'      : 'ยังไม่มีประกาศสัตว์หาย',
      'list.empty_found'     : 'ยังไม่มีประกาศสัตว์เลี้ยงที่พบ',
      'list.empty_btn_lost'  : 'ลงประกาศสัตว์หายเป็นคนแรก',
      'list.empty_btn_found' : 'แจ้งสัตว์เลี้ยงที่พบเป็นคนแรก',
      'list.resolved'        : '✅ ส่งคืนเจ้าของแล้ว',

      /* ── Pet detail ── */
      'detail.badge_lost'          : '🚨 สัตว์เลี้ยงหาย',
      'detail.badge_found'         : '💚 พบสัตว์เลี้ยง',
      'detail.badge_resolved'      : '✅ ปิดประกาศแล้ว',
      'detail.label_type'          : 'ชนิด',
      'detail.label_breed'         : 'สายพันธุ์',
      'detail.label_gender'        : 'เพศ',
      'detail.label_age'           : 'อายุ',
      'detail.label_color'         : 'สี / ลักษณะ',
      'detail.label_loc_lost'      : 'สถานที่หาย',
      'detail.label_loc_found'     : 'สถานที่พบ',
      'detail.label_lost_date'     : 'วันที่หาย',
      'detail.label_found_date'    : 'วันที่พบ',
      'detail.reward_label'        : 'รางวัลสำหรับผู้พบน้อง',
      'detail.contact_warning'     : '⚠️ ใช้ข้อมูลติดต่อเพื่อช่วยเหลือเคสนี้เท่านั้น กรุณาอย่าเผยแพร่ต่อ',
      'detail.contact'             : 'ติดต่อ',
      'detail.gate_hint'           : 'ติดต่อผู้โพส',
      'detail.gate_social'         : '🔗 มีลิงก์โซเชียล (ล็อกอินเพื่อดู)',
      'detail.gate_lock'           : '🔒 ล็อกอินเพื่อดูข้อมูลติดต่อเต็ม',
      'detail.gate_login_btn'      : 'เข้าสู่ระบบ →',
      'detail.social_link'         : 'ดูโพสต์โซเชียล ↗',
      'detail.btn_gmap'            : '📍 ดูแผนที่ใน Google Maps ↗',
      'detail.btn_resolve_lost'    : '✅ พบน้องแล้ว — ปิดประกาศ',
      'detail.btn_resolve_found'   : '✅ ส่งคืนเจ้าของแล้ว — ปิดประกาศ',
      'detail.btn_edit'            : '✏️ แก้ไขประกาศ',
      'detail.btn_delete'          : '🗑️ ลบประกาศ',
      'detail.btn_share'           : '↗ แชร์',
      'detail.btn_copy'            : '🔗 คัดลอก',
      'detail.similar'             : '🐾 ประกาศที่คล้ายกัน',
      'detail.comments_title'      : '💬 ความเห็น',
      'detail.comment_placeholder' : 'ฝากข้อความช่วยเหลือ ให้กำลังใจ หรือเบาะแส...',
      'detail.comment_submit'      : 'ส่งความเห็น',
      'detail.comment_empty'       : 'ยังไม่มีความเห็น เป็นคนแรกได้เลย!',

      /* ── Common ── */
      'common.back'   : '← ย้อนกลับ',
      'common.search' : 'ค้นหา',
    },

    en: {
      /* ── Navbar ── */
      'nav.home'          : 'Home',
      'nav.lost'          : 'Lost Pets',
      'nav.found'         : 'Found Pets',
      'nav.map'           : '🗺️ Map',
      'nav.ai_search'     : '🔍 AI Search',
      'nav.products'      : 'Products',
      'nav.blog'          : 'Articles',
      'nav.login'         : 'Login',
      'nav.profile'       : '👤 Profile ▾',
      'nav.my_profile'    : '⚙️ My Profile',
      'nav.my_posts'      : '📢 My Posts',
      'nav.report_lost'   : '➕ Report Lost',
      'nav.report_found'  : '🐾 Report Found',
      'nav.logout'        : '🚪 Logout',

      /* ── Footer ── */
      'ft.tagline'        : 'AI-powered lost pet finder — helping pets return home safely 🐾',
      'ft.browse'         : 'Browse',
      'ft.lost'           : 'Lost Pets',
      'ft.found'          : 'Found Pets',
      'ft.map'            : 'Map',
      'ft.ai_search'      : 'AI Search',
      'ft.community'      : 'Community',
      'ft.blog'           : 'Articles',
      'ft.products'       : 'Products',
      'ft.report_lost'    : 'Report Lost',
      'ft.report_found'   : 'Report Found',
      'ft.login'          : 'Login',
      'ft.signup'         : 'Sign Up',

      /* ── Lost / Found list ── */
      'list.hero_lost'       : 'Lost Pets',
      'list.hero_found'      : 'Found Pets',
      'list.hero_sub'        : 'Listed Below',
      'list.btn_report_lost' : '+ Report Lost Pet',
      'list.btn_report_found': '+ Report Found Pet',
      'list.btn_view_found'  : 'View Found',
      'list.btn_view_lost'   : 'View Lost',
      'list.search_text'     : 'Search by name, breed or location',
      'list.search_ai'       : 'Image Search (AI)',
      'list.search_btn'      : 'Search',
      'list.hint_text_lost'  : 'Filter lost pet posts directly',
      'list.hint_text_found' : 'Filter found pet posts directly',
      'list.hint_ai'         : 'Upload a photo for AI-powered matching',
      'list.search_label'    : 'Results for',
      'list.found_dash'      : '—',
      'list.count_pre'       : '',
      'list.result_unit'     : 'posts',
      'list.clear'           : 'Clear search',
      'list.badge_pet'       : 'Pet',
      'list.badge_lost'      : 'Lost',
      'list.badge_found'     : 'Found',
      'list.label_gender'    : 'Gender',
      'list.label_age'       : 'Age',
      'list.empty_lost'      : 'No lost pet posts yet',
      'list.empty_found'     : 'No found pet posts yet',
      'list.empty_btn_lost'  : 'Be the first to post',
      'list.empty_btn_found' : 'Be the first to report',
      'list.resolved'        : '✅ Returned to owner',

      /* ── Pet detail ── */
      'detail.badge_lost'          : '🚨 Lost Pet',
      'detail.badge_found'         : '💚 Found Pet',
      'detail.badge_resolved'      : '✅ Case Closed',
      'detail.label_type'          : 'Type',
      'detail.label_breed'         : 'Breed',
      'detail.label_gender'        : 'Gender',
      'detail.label_age'           : 'Age',
      'detail.label_color'         : 'Color / Markings',
      'detail.label_loc_lost'      : 'Last Seen',
      'detail.label_loc_found'     : 'Found Location',
      'detail.label_lost_date'     : 'Date Lost',
      'detail.label_found_date'    : 'Date Found',
      'detail.reward_label'        : 'Reward for finder',
      'detail.contact_warning'     : '⚠️ Use contact info for this case only. Please do not share.',
      'detail.contact'             : 'Contact',
      'detail.gate_hint'           : 'Contact poster',
      'detail.gate_social'         : '🔗 Has social link (login to view)',
      'detail.gate_lock'           : '🔒 Login to see full contact info',
      'detail.gate_login_btn'      : 'Login →',
      'detail.social_link'         : 'View Social Post ↗',
      'detail.btn_gmap'            : '📍 View on Google Maps ↗',
      'detail.btn_resolve_lost'    : '✅ Pet Found — Close Post',
      'detail.btn_resolve_found'   : '✅ Returned to Owner — Close Post',
      'detail.btn_edit'            : '✏️ Edit Post',
      'detail.btn_delete'          : '🗑️ Delete Post',
      'detail.btn_share'           : '↗ Share',
      'detail.btn_copy'            : '🔗 Copy Link',
      'detail.similar'             : '🐾 Similar Posts',
      'detail.comments_title'      : '💬 Comments',
      'detail.comment_placeholder' : 'Leave a tip, message of support, or sighting info...',
      'detail.comment_submit'      : 'Send',
      'detail.comment_empty'       : 'No comments yet. Be the first!',

      /* ── Common ── */
      'common.back'   : '← Back',
      'common.search' : 'Search',
    },
  };

  // ─────────────────────────────────────────────
  // ENGINE
  // ─────────────────────────────────────────────
  let currentLang = DEFAULT_LANG;

  function getLang() {
    try { return localStorage.getItem(STORAGE_KEY) || DEFAULT_LANG; } catch (_) { return DEFAULT_LANG; }
  }
  function saveLang(lang) {
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (_) {}
  }

  function applyLang(lang) {
    currentLang = lang;
    const dict = T[lang] || T[DEFAULT_LANG];

    document.querySelectorAll('[data-i18n]').forEach(el => {
      const v = dict[el.getAttribute('data-i18n')];
      if (v !== undefined) el.textContent = v;
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const v = dict[el.getAttribute('data-i18n-placeholder')];
      if (v !== undefined) el.placeholder = v;
    });
    document.querySelectorAll('[data-i18n-aria]').forEach(el => {
      const v = dict[el.getAttribute('data-i18n-aria')];
      if (v !== undefined) el.setAttribute('aria-label', v);
    });

    document.documentElement.lang = lang === 'en' ? 'en' : 'th';

    // Update toggle button highlight
    document.querySelectorAll('.lang-opt').forEach(opt => {
      opt.classList.toggle('active', opt.dataset.lang === lang);
    });
  }

  function setLang(lang) {
    saveLang(lang);
    applyLang(lang);
  }

  function init() {
    currentLang = getLang();
    applyLang(currentLang);

    // Wire up toggle button (inserted by base.html)
    document.addEventListener('click', (e) => {
      const opt = e.target.closest('.lang-opt[data-lang]');
      if (opt) setLang(opt.dataset.lang);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.PF        = window.PF || {};
  window.PF.setLang = setLang;
  window.PF.getLang = getLang;
  window.PF.t       = (key) => (T[currentLang] || T[DEFAULT_LANG])[key] || key;
})();

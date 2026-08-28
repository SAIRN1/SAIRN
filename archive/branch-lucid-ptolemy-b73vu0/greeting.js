// ═══════════════════════════════════════════════════════════════════
//  SAIRN Technologies — /api/greeting
//  First Message Magic — the WOW moment in 10 seconds
//
//  Called when any SAIRN app loads. Returns a personalized opening
//  message from Claude before the user types a single word.
//
//  Uses: time of day · day of week · app context · user memory
//  Cost: ~50 tokens per greeting (~$0.00025) — negligible
//
//  Michael L. Dibert · SAIRN Technologies · 2026
// ═══════════════════════════════════════════════════════════════════

import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@supabase/supabase-js";

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const supabase  = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
const MODEL     = "claude-haiku-4-5-20251001";

// ── APP PERSONALITIES ─────────────────────────────────────────────
const APP_GREETINGS = {
  mind: {
    name: "SAIRN Mind",
    icon: "🧠",
    day:   ["How are you feeling today? Take a breath — you've got this.", "Good day. How's your head and heart today?", "Before the day gets loud — how are you doing?"],
    afternoon: ["How's your energy holding up today?", "Afternoon check-in — how are you feeling right now?", "Midday pause. How's your mental space today?"],
    evening:   ["How did today treat you?", "Evening. What's on your mind tonight?", "Winding down. Anything weighing on you today?"],
    night:     ["Still up. What's on your mind?", "It's late — sometimes that's when thoughts get loudest. Want to talk?", "Late night thoughts are often the most important ones. What's going on?"],
    monday:    ["New week. How are you approaching it?"],
    sunday:    ["Sunday evenings can feel heavy. How are you doing?"],
  },
  kitchen: {
    name: "SAIRN Kitchen",
    icon: "🍽️",
    day:   ["Good day! What's the plan for meals today?", "Hey — want me to help you figure out dinner now so you're not scrambling at 5pm?", "Good day! What do you have in the fridge right now?"],
    afternoon: ["Afternoon hunger incoming. What are you thinking for dinner?", "Good afternoon! Staring into the fridge wondering what to make? Tell me what you've got.", "What's on the menu tonight?"],
    evening:   ["Dinner time! What do you feel like cooking — or would you prefer something quick?", "Evening! What are you working with tonight?", "What's in your kitchen right now? Let's make something good."],
    night:     ["Late night kitchen raid? Tell me what you've got and I'll make it work.", "Meal planning for tomorrow? Good idea — let's set you up."],
    monday:    ["New week — want to plan meals for the whole week right now and get it out of the way?"],
    friday:    ["Friday! Want something special for dinner tonight, or keeping it simple?"],
  },
  family: {
    name: "SAIRN Family",
    icon: "👨‍👩‍👧‍👦",
    day:   ["Good day! What's the family dealing with today?", "Hey! Anything going on with the kids or household I can help with?", "Good day. What does today look like for your family?"],
    afternoon: ["Afternoon — homework starting soon? Or something else going on?", "How's the family doing today?", "Anything coming up with the kids I can help you prepare for?"],
    evening:   ["How did everyone's day go?", "Evening family check-in — what needs handling tonight?", "How are the kids? Anything on your mind about the family?"],
    night:     ["Quiet hour — good time to think about the family. What's on your mind?"],
    sunday:    ["Sunday — great time to prep for the week ahead. What's coming up for your family?"],
    monday:    ["New week for the whole family. Anything you want to get ahead of?"],
  },
  career: {
    name: "SAIRN Career",
    icon: "💼",
    day:   ["Good day. What are you working on career-wise today?", "Hey — job search, work challenge, or something else I can help with?", "Good day! Ready to work on your career? What's the focus today?"],
    afternoon: ["Afternoon — got a career question or project I can help move forward?", "What's the career priority right now?", "Good afternoon. Resume, interview prep, or something else?"],
    evening:   ["Evening is great for career work when the day's chaos settles. What are you working on?", "What career goal are you focused on tonight?", "Evening career session — what do you want to make progress on?"],
    night:     ["Late night career work — driven. What are you focusing on?"],
    monday:    ["New week — great time to make career moves. What's the goal this week?"],
    friday:    ["End of the week — any career wins to build on, or prep for next week?"],
  },
  home: {
    name: "SAIRN Home",
    icon: "🏠",
    day:   ["Good day! Any home or housing questions on your mind today?", "Hey — what's going on with your home or rental situation?", "Good day. Mortgage, repairs, HOA, or something else?"],
    afternoon: ["What home situation can I help you navigate today?", "Afternoon — any housing questions I can help clarify?", "What's going on with the home front?"],
    evening:   ["Evening — great time to review documents or figure out a home situation. What's up?", "What housing question has been on your mind?", "What can I help you understand about your home or lease?"],
    night:     ["Late night worrying about the house? Let's talk through it.", "What home situation is keeping you up?"],
    sunday:    ["Sunday — good time to deal with home admin. What needs attention?"],
  },
  shield: {
    name: "SAIRN Shield",
    icon: "🛡️",
    day:   ["Good day. Any insurance or benefits questions I can help decode?", "Hey — what insurance or medical bill situation can I help you navigate?", "Good day. EOB, denial, or policy question?"],
    afternoon: ["What insurance situation do you need to fight today?", "What benefits question can I help clarify?", "Got a claim, denial, or confusing document? Let's look at it."],
    evening:   ["Evening — good time to deal with insurance paperwork. What do you have?", "What insurance situation has been on your mind today?", "What can I help you understand or fight?"],
    night:     ["Insurance stress at night is the worst. What's going on?", "Let's get this insurance thing sorted. What happened?"],
    monday:    ["New week — any insurance paperwork that came in over the weekend?"],
  },
  daily: {
    name: "SAIRN Daily",
    icon: "📱",
    day:   ["Good day! Ready to map out your day?", "Hey! Let's get today organized. What's on your plate?", "Good day. What are the top 3 things that need to happen today?"],
    afternoon: ["Afternoon check-in — staying on track?", "How's the day going? Anything to reprioritize?", "Midday — what still needs to get done today?"],
    evening:   ["Evening — let's review today and set up tomorrow.", "How did today go? What carries over to tomorrow?", "Evening wind-down. What got done, what didn't, what's first tomorrow?"],
    night:     ["Before you sleep — top 3 for tomorrow?", "Good night coming. Brain dump everything that's on your mind.", "Last thing — what absolutely has to happen tomorrow?"],
    monday:    ["Monday! Let's make this week count. What are you working toward?"],
    friday:    ["Friday — let's close out the week and plan a good one next week."],
    sunday:    ["Sunday planning session. What does this week look like?"],
  },
  health: {
    name: "SAIRN Health",
    icon: "❤️",
    day:   ["Good day! How are you feeling today?", "Health check — how's your body today?", "How did you sleep? How are you feeling?"],
    afternoon: ["Afternoon — any health questions on your mind?", "How's your energy today?", "What health question can I help with today?"],
    evening:   ["Evening — any health concerns from today?", "How did your body feel today?", "What health topic is on your mind tonight?"],
    night:     ["Can't sleep? Let's talk about it.", "Late night health worry? Let's address it.", "What's going on health-wise that's keeping you up?"],
  },
  money: {
    name: "SAIRN Money",
    icon: "💰",
    day:   ["Good day! Any money questions on your mind today?", "Hey — budget, savings, or financial question?", "Good day. What financial goal are you working on?"],
    afternoon: ["What money situation can I help with today?", "Afternoon financial check-in — what's on your mind?"],
    evening:   ["Good time to look at finances. What's going on?", "What money question has been on your mind today?"],
    night:     ["Lying awake about money? Let's work through it."],
  },
  legal: {
    name: "SAIRN Legal",
    icon: "⚖️",
    day:   ["Good day. Any legal documents or questions I can help with today?", "Hey — what legal situation can I help you understand?"],
    afternoon: ["What legal question is on your mind?", "Got a document to review or a rights question?"],
    evening:   ["What legal situation needs clarity tonight?", "Evening — good time to work through legal documents. What do you have?"],
    night:     ["Legal stress late at night is rough. What's going on?"],
  },
  study: {
    name: "SAIRN Study",
    icon: "📚",
    day:   ["Good day! What are we studying today?", "Study session — what's the subject?"],
    afternoon: ["Afternoon study time! What topic needs work?", "What are you trying to understand or learn today?"],
    evening:   ["Evening study session — what's on the syllabus?", "What are you working on tonight?"],
    night:     ["Late night studying — dedicated. What are we tackling?"],
  },
  roam: {
    name: "SAIRN Roam",
    icon: "✈️",
    day:   ["Good day! Planning a trip or dreaming about one?", "Hey — where are you thinking about going?"],
    afternoon: ["What travel question can I help with today?", "Planning a trip or need travel advice?"],
    evening:   ["Evening trip planning — where to?", "What adventure are you dreaming up?"],
    night:     ["Late night travel dreaming — where do you want to go?"],
  },
  lingual: {
    name: "SAIRN Lingual",
    icon: "🌍",
    day:   ["Good day! Which language are we working on today?", "Language practice — ready?"],
    afternoon: ["Language practice time! What are we working on?"],
    evening:   ["Evening language session — consistency is everything. What language?"],
    night:     ["Late night language study — committed. What are we practicing?"],
  },
  senior: {
    name: "SAIRN Senior",
    icon: "🤝",
    day:   ["Good day! How are you feeling today? What can I help you with?", "Good day. Is there anything you need help with today?"],
    afternoon: ["Good afternoon! What can I help you with today?", "How are you doing this afternoon?"],
    evening:   ["Good evening! How was your day? What can I help with?"],
    night:     ["Good evening. Can't sleep? Happy to keep you company or help with something."],
  },
  sairntype: {
    name: "SAIRNtype",
    icon: "⌨️",
    day:   ["Good day! What are we writing today?", "Hey — what needs to be written?"],
    afternoon: ["What writing project can I help with?", "What are you working on writing-wise?"],
    evening:   ["Evening writing session — what are we crafting?"],
    night:     ["Late night writing — ideas flow at night. What are we working on?"],
  },
};

// Default fallback
const DEFAULT_APP = {
  day:   ["Good day! What can I help you with today?"],
  afternoon: ["Good afternoon! What can I help you with?"],
  evening:   ["Good evening! What can I help you with tonight?"],
  night:     ["Still up — what do you need?"],
};

function getTimeSlot(hour) {
  if (hour >= 5  && hour < 12) return "day";
  if (hour >= 12 && hour < 17) return "afternoon";
  if (hour >= 17 && hour < 21) return "evening";
  return "night";
}

function getDayKey(day) {
  const days = ["sunday","monday","tuesday","wednesday","thursday","friday","saturday"];
  return days[day];
}

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", process.env.SITE_URL || "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "POST")    return res.status(405).end();

  const { app_id, client_hour, client_day } = req.body || {};
  if (!app_id) return res.status(400).json({ error: "app_id required" });

  const hour    = parseInt(client_hour) || new Date().getHours();
  const day     = parseInt(client_day)  || new Date().getDay();
  const slot    = getTimeSlot(hour);
  const dayKey  = getDayKey(day);
  const appConf = APP_GREETINGS[app_id] || DEFAULT_APP;

  // Load user memory if authenticated
  let memoryContext = "";
  const authHeader = req.headers.authorization;
  if (authHeader?.startsWith("Bearer ")) {
    try {
      const { data: { user } } = await supabase.auth.getUser(authHeader.slice(7));
      if (user) {
        const { data: memory } = await supabase
          .from("user_memory").select("facts,summary").eq("user_id", user.id).single();

        if (memory?.facts?.length) {
          const relevantFacts = memory.facts
            .filter(f => f.confidence !== "low")
            .slice(-15)
            .map(f => `- ${f.fact}`)
            .join("\n");
          memoryContext = `\n\nWhat you know about this user:\n${relevantFacts}${memory.summary ? `\nSummary: ${memory.summary}` : ""}`;
        }
      }
    } catch {}
  }

  // Pick a base greeting (day-specific or time-slot)
  const dayGreetings = appConf[dayKey];
  const baseGreetings = (dayGreetings && Math.random() > 0.6)
    ? dayGreetings
    : (appConf[slot] || DEFAULT_APP[slot]);
  const baseGreeting = pick(baseGreetings);

  // If no memory, return the base greeting directly (fast path, no API call)
  if (!memoryContext) {
    return res.status(200).json({
      greeting: baseGreeting,
      personalized: false,
      slot,
    });
  }

  // With memory — ask Claude to personalize the greeting
  try {
    const response = await anthropic.messages.create({
      model: MODEL,
      max_tokens: 80,
      messages: [{
        role: "user",
        content: `You are ${appConf.name || app_id}, part of the SAIRN platform. 

It is ${slot} (${hour}:00) on a ${dayKey}.
${memoryContext}

Write ONE short, warm, personalized opening message (1-2 sentences max). 
Base it on: "${baseGreeting}"
Make it feel personal using what you know — but naturally, not robotically.
Do not start with "I know" or "I remember". Just be warm and specific.
Respond with ONLY the message, nothing else.`
      }]
    });

    const personalized = response.content?.[0]?.text?.trim() || baseGreeting;

    return res.status(200).json({
      greeting: personalized,
      personalized: true,
      slot,
    });

  } catch {
    // Fallback to base greeting if Claude call fails
    return res.status(200).json({
      greeting: baseGreeting,
      personalized: false,
      slot,
    });
  }
}

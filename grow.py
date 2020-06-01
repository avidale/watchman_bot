import yaml
import random

from dialogue_manager import Intents

COACH_INTRO = """Окей! Сейчас я задам около 10-15 вопросов, которые помогут вам достичь цели."""


def preprocess_quiz(quiz):
    """ Assign probability to each question or question series """
    default_num_questions = quiz.get('default', {}).get('default_num_questions', 3)

    for step in quiz['steps']:
        new_questions = []
        num_questions = step.get('num_questions', default_num_questions)
        free_proba = num_questions
        questions_to_distribute = 0
        for question_block in step['questions']:
            if isinstance(question_block, str):
                question_block = {'q': question_block}
            if isinstance(question_block['q'], str):
                question_block['q'] = [question_block['q']]
            if 'p' in question_block:
                free_proba -= question_block['p']
            else:
                questions_to_distribute += 1
            new_questions.append(question_block)
        proba_to_fill = max(1.0, free_proba) / questions_to_distribute
        for question in new_questions:
            if 'p' not in question:
                question['p'] = proba_to_fill
        step['questions'] = new_questions
    return quiz


def sample_next_question(quiz, position=None):
    """ Generate the next question from the quiz """
    if position is None:
        position = (0, 0, -1)
    step_id, question_id, subquestion_id = position
    response = 'Что-то пошло не так'
    is_end = False
    while True:
        if step_id >= len(quiz['steps']):
            response = 'Кажется, пора заканчивать. Как вам эта сессия?'
            is_end = True
            break
        current_step_questions = quiz['steps'][step_id].get('questions', [])
        if question_id >= len(current_step_questions):
            step_id += 1
            question_id = 0
            subquestion_id = -1
            continue
        current_question = current_step_questions[question_id]
        if subquestion_id == -1:
            if random.uniform(0, 1) > current_question['p']:
                question_id += 1
                continue
        current_question_subquestions = current_question['q']
        subquestion_id += 1
        if subquestion_id >= len(current_question_subquestions):
            question_id += 1
            subquestion_id = -1
            continue
        response = current_question_subquestions[subquestion_id]
        break
    return response, is_end, (step_id, question_id, subquestion_id)


with open('data/grow.yaml', 'r', encoding='utf-8') as f:
    QUIZ = preprocess_quiz(yaml.safe_load(f))


def reply_with_coach(text, user_object=None, intent=None):
    if user_object is None:
        user_object = {}
    coach_state = user_object.get('coach_state', {}) or {}
    coach_state['intro'] = False
    if intent == Intents.GROW_COACH_EXIT:
        coach_state['ask_feedback'] = True
        response = 'Хорошо, закончим на этом. Как вам эта сессия?'
    elif intent == Intents.GROW_COACH_FEEDBACK:
        coach_state = {}
        response = 'Спасибо за обратную связь! \U0001F60A' \
                   '\nМне будет приятно, если вы подробнее опишете: ' \
                   'что понравилось, что не понравилось, как можно улучшить этот сценарий.'
    elif not coach_state.get('is_active') or intent == Intents.GROW_COACH_INTRO:
        coach_state = {'is_active': True, 'intro': True, 'question_count': 0}
        response = COACH_INTRO
    else:
        qc = coach_state.get('question_count') or 0
        qc += 1
        # todo: maybe, ask something based on the text
        response, is_end, position = sample_next_question(QUIZ, coach_state.get('position'))
        if is_end:
            coach_state['ask_feedback'] = True
        else:
            response = '{}. {}'.format(qc, response)
            coach_state['position'] = position
        coach_state['question_count'] = qc
    return response, {"$set": {'coach_state': coach_state}}

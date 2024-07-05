import asyncio
import os
import threading
import time
import uuid
import logging
from typing import Any

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import spotipy
from flask_socketio import SocketIO, emit, join_room, leave_room
from pymongo import MongoClient
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import math

from PAR.Single_Chain.MultiQueryChain import DerivedQueries
from PAR.main import build_PAR_graph
from jpop_translate import run_translate
from search import run_tavily_search, run_brave_search

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')
if not app.secret_key:
    raise ValueError("No SECRET_KEY set for Flask application")


socketio = SocketIO(app, server_options={'cors_allowed_origin': '*'})





# Spotify API 자격 증명 설정
client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
spotify_redirect_uri = "http://localhost:5000/callback"
SCOPE = 'user-read-private user-read-email user-modify-playback-state user-read-playback-state streaming'

# Spotify 클라이언트 설정
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=spotify_redirect_uri,
    scope=SCOPE,
    show_dialog=True
)


# MongoDB 연결
library_collection = MongoClient(host=os.getenv('MONGODB_URI')).get_database('song').get_collection('JPOP')

ITEMS_PER_PAGE = 20  # 페이지당 항목 수

par_tasks = {}


def run_async_task(task_id):
    print(f'Running task {task_id}')
    asyncio.run(run_par_task(task_id))

PAR_STAGES = {
    'transform_new_query': 5,
    'multi_query_generator': 5,
    'retrieve_vector_db': 5,
    'grade_each_documents': 5,
    'THLO': 30,
    'Composable_Search': 40,
    'Generate_Conclusion': 5,
    'Generate': 4
}
TOTAL_PROGRESS = sum(PAR_STAGES.values())


@socketio.on('connect')
def handle_connect():
    print(f'Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join')
def on_join(data):
    task_id = data['task_id']
    join_room(task_id)
    print(f'Client joined room: {task_id}')
    emit('joined', {'task_id': task_id}, )

@socketio.on('leave')
def on_leave(data):
    task_id = data['task_id']
    leave_room(task_id)
    print(f'Client left room: {task_id}')


@socketio.on('start_par')
def handle_start_par(data):
    query = data['query']
    task_id = str(uuid.uuid4())
    par_tasks[task_id] = {
        'status': 'running',
        'progress': 0,
        'query': query,
        'completed_stages': [],
        'current_stage': ''
    }

    join_room(task_id)
    emit('par_started', {'task_id': task_id}, )
    socketio.start_background_task(run_async_task, task_id)


@socketio.on('resume_par')
def handle_resume_par(data):
    task_id = data['task_id']
    print(f'Resuming task {task_id}')
    if task_id in par_tasks:
        print('par_Status_update')
        emit('par_status_update', par_tasks[task_id])
    else:
        print('par_error')
        emit('par_error', {'error': 'PAR task not found'})


@socketio.on('get_par_status')
def handle_get_par_status(data):
    task_id = data['task_id']
    if task_id in par_tasks:
        print('par_status_update')
        emit('par_status_update', par_tasks[task_id])
    else:
        print('par_error')
        emit('par_error', {'error': 'PAR task not found'})


@socketio.on('cancel_par')
def handle_cancel_par(data):
    task_id = data['task_id']
    if task_id in par_tasks:
        # 여기에 PAR 작업을 취소하는 로직 추가
        del par_tasks[task_id]
        emit('par_cancelled', {'task_id': task_id})
    else:
        emit('par_error', {'error': 'PAR task not found'})


async def update_task_status(task_id, node_name: str):
    if task_id in par_tasks:
        if 'completed_stages' not in par_tasks[task_id]:
            par_tasks[task_id]['completed_stages'] = []
        if node_name not in par_tasks[task_id]['completed_stages']:
            par_tasks[task_id]['completed_stages'].append(node_name)

        completed_stages = par_tasks[task_id]['completed_stages']
        progress = sum(PAR_STAGES[s] for s in completed_stages)
        par_tasks[task_id]['progress'] = int((progress / TOTAL_PROGRESS) * 100)
        par_tasks[task_id]['current_stage'] = node_name

    print(f"par_status_update: {par_tasks[task_id]}")
    socketio.emit('par_status_update', par_tasks[task_id])


async def run_par_task(task_id):
    print(f'Task {task_id} started')
    try:
        # par_graph = build_PAR_graph()
        # query = par_tasks[task_id]['query']
        #
        # async def callback(node_name: str, _result: Any = None):
        #     print(f'callback called node_name: {node_name}')
        #     if node_name == "user_input":
        #         par_tasks[task_id]['awaiting_input'] = True
        #         par_tasks[task_id]['input_data'] = _result
        #         socketio.emit('par_input_required', {'task_id': task_id, 'input_data': _result})
        #
        #         while par_tasks[task_id].get('user_response') is None:
        #             await asyncio.sleep(1)
        #         user_response = par_tasks[task_id]['user_response']
        #         del par_tasks[task_id]['user_response']
        #         del par_tasks[task_id]['awaiting_input']
        #         return user_response
        #     else:
        #         print(f'callback called node_name is not user_input')
        #         try:
        #             await update_task_status(task_id, node_name)
        #         except Exception as e:
        #             print(f"Error updateing task status: {e}")
        #
        #
        # inputs = {
        #     "user_question": query,
        #     "callback": callback
        # }

        # result = await par_graph.ainvoke(inputs, config={})
        time.sleep(5)

        final_result = {}

        result = {'user_question': '버블정렬의 시간복잡도와 공간복잡도에 대해 알려줘', 'original_query': 'What are the time complexity and space complexity of the bubble sort algorithm? Provide a brief explanation for each, including best-case and worst-case scenarios.', 'derived_queries': DerivedQueries(derived_query_1='bubble sort algorithm time complexity', derived_query_2='bubble sort algorithm space complexity', derived_query_3='best case and worst case bubble sort algorithm'), 'document_title': 'Comprehensive Analysis of Bubble Sort Algorithm: Time and Space Complexity', 'document_description': 'To provide a thorough understanding of the time and space complexity of the bubble sort algorithm, including best-case and worst-case scenarios, practical implications, and comparisons with other sorting algorithms.', 'fast_search_results': '<Relevant Quotes>\n<Quote & URL>\nQuote: "The best case for bubble sort occurs when the array is already sorted. In this case, the number of comparisons required is N-1, and the number of swaps required is 0. Hence, the best-case complexity is O(N)."\nURL: https://www.geeksforgeeks.org/time-and-space-complexity-analysis-of-bubble-sort/\n</Quote & URL>\n<Quote & URL>\nQuote: "The worst-case condition for bubble sort occurs when the elements of the array are arranged in decreasing order. In this case, the time complexity of bubble sort is O(n^2)."\nURL: https://www.geeksforgeeks.org/time-and-space-complexity-analysis-of-bubble-sort/\n</Quote & URL>\n<Quote & URL>\nQuote: "The space complexity of bubble sort is O(1), as it only requires a constant amount of additional space during the sorting process."\nURL: https://www.geeksforgeeks.org/time-and-space-complexity-analysis-of-bubble-sort/\n</Quote & URL>\n</Relevant Quotes>\n\n<Answer>\nThe time complexity of the bubble sort algorithm is:\n- Best case: O(n)\n- Worst case: O(n^2)\n- Average case: O(n^2)\n\nThe best-case scenario for bubble sort occurs when the input array is already sorted, requiring only N-1 comparisons and 0 swaps. The worst-case scenario occurs when the array is in decreasing order, resulting in the maximum number of comparisons and swaps, leading to a time complexity of O(n^2).\n\nThe space complexity of bubble sort is O(1), as it is an in-place sorting algorithm that only requires a constant amount of additional space during the sorting process.\n</Answer>', 'search_continue': True, 'keys': {'generation': '<scratchpad>\n사용자의 질문은 버블 정렬의 시간복잡도와 공간복잡도에 대한 정보를 요구하고 있습니다. 문서를 분석하여 이에 대한 정보를 찾아보겠습니다.\n\n시간복잡도:\n- 최악의 경우: O(n^2)\n- 최선의 경우: O(n)\n- 평균적인 경우: O(n^2)\n\n공간복잡도:\n- O(1)\n\n이 정보를 바탕으로 버블 정렬의 시간복잡도와 공간복잡도에 대해 상세히 설명하고, 각 경우에 대한 설명과 실제 적용 시의 의미를 포함하여 답변을 작성하겠습니다.\n</scratchpad>\n\n버블 정렬의 시간복잡도와 공간복잡도에 대해 다음과 같이 설명드릴 수 있습니다:\n\n시간복잡도:\n1. 최악의 경우: O(n^2)\n   - 입력 배열이 역순으로 정렬되어 있을 때 발생합니다.\n   - 이 경우, 알고리즘은 모든 요소를 비교하고 교환해야 합니다.\n\n2. 최선의 경우: O(n)\n   - 입력 배열이 이미 오름차순으로 정렬되어 있을 때 발생합니다.\n   - 이 경우, 알고리즘은 단 한 번의 패스로 정렬이 완료됩니다.\n\n3. 평균적인 경우: O(n^2)\n   - 일반적으로 입력 배열이 무작위로 정렬되어 있을 때 발생합니다.\n   - 최악의 경우와 마찬가지로 많은 비교와 교환이 필요합니다.\n\n문서에 따르면, "버블 정렬의 시간복잡도는 최악의 경우 O(n^2)입니다. 이는 알고리즘의 실행 시간이 입력 크기의 제곱에 비례하여 증가한다는 것을 의미합니다." 이러한 특성으로 인해 버블 정렬은 대규모 데이터셋에 대해 비효율적입니다.\n\n공간복잡도:\n버블 정렬의 공간복잡도는 O(1)입니다. 이는 알고리즘이 입력 크기와 관계없이 일정한 추가 메모리만을 사용한다는 것을 의미합니다. 문서에서는 "버블 정렬은 제자리 정렬 알고리즘으로, 요소 교환을 위한 임시 변수만을 사용하여 추가적인 메모리 할당 없이 입력 배열을 직접 수정합니다."라고 설명하고 있습니다.\n\n실제 적용 시의 의미:\n버블 정렬의 O(n^2) 시간복잡도는 대규모 데이터셋에 대해 매우 비효율적이며, 실행 시간이 급격히 증가할 수 있습니다. 그러나 O(1)의 공간복잡도는 메모리 사용이 제한된 환경에서 유용할 수 있습니다. 문서에 따르면, "버블 정렬의 단순성과 안정성은 교육적 목적으로 가치가 있지만, 실제 응용에서는 일반적으로 작은 데이터셋이나 메모리 사용이 주요 관심사인 시나리오로 제한됩니다."\n\n따라서 버블 정렬은 교육적 목적이나 소규모 데이터셋에는 적합할 수 있지만, 대규모 데이터 처리가 필요한 현대적인 소프트웨어 개발에서는 퀵정렬이나 병합정렬과 같은 더 효율적인 알고리즘이 선호됩니다.', 'full_documents': '# Comprehensive Analysis of Bubble Sort Algorithm: Time and Space Complexity\n\n## What are the time complexity and space complexity of the bubble sort algorithm? Provide a brief explanation for each, including best-case and worst-case scenarios.\n\nTo provide a thorough understanding of the time and space complexity of the bubble sort algorithm, including best-case and worst-case scenarios, practical implications, and comparisons with other sorting algorithms.\n\n\n\n\n## Introduction to Algorithm Analysis\n\nAlgorithm analysis is a fundamental concept in computer science that focuses on understanding the efficiency and performance of different algorithms. By analyzing the complexity of algorithms, developers can make informed decisions about which algorithms to use for a given problem, ensuring that their software can handle large input sizes efficiently.\n\nAt the heart of algorithm analysis lies the concept of algorithm complexity, which describes the amount of resources (such as time and memory) required by an algorithm to solve a problem. Understanding algorithm complexity is crucial, as it allows us to compare the efficiency of different algorithms and predict how they will scale as the input size increases.\n\n## The Bubble Sort Algorithm\n\nOne of the simplest sorting algorithms is the bubble sort algorithm. Bubble sort works by repeatedly comparing adjacent elements in a list and swapping them if they are in the wrong order. This process is repeated until the entire list is sorted.\n\nThe bubble sort algorithm works as follows:\n\n1. Compare the first two elements in the list.\n2. If the first element is greater than the second element, swap them.\n3. Move to the next pair of elements and repeat step 2.\n4. Repeat steps 1-3 until the entire list is sorted.\n\nThis process is like bubbles rising to the surface of a liquid, as the larger elements "bubble up" to the end of the list during each pass.\n\n## Time and Space Complexity\n\nThe time complexity of an algorithm describes how the algorithm\'s execution time grows with the size of the input. In the case of bubble sort, the time complexity is O(n^2) in the worst case, meaning that the algorithm\'s running time increases quadratically with the size of the input.\n\nThis is because bubble sort requires n passes through the list, with n-1 comparisons in each pass, resulting in a total of n(n-1)/2 comparisons. As the input size increases, the number of comparisons grows rapidly, making bubble sort inefficient for large datasets.\n\nIn addition to time complexity, algorithm analysis also considers space complexity, which describes the amount of memory required by an algorithm to solve a problem. Bubble sort has a space complexity of O(1), as it only requires a constant amount of additional memory to store temporary variables for swapping elements.\n\n## Importance of Algorithm Complexity in Programming\n\nUnderstanding algorithm complexity is crucial for software development, as it allows developers to choose the most appropriate algorithms for their applications. Algorithms with better time complexity, such as O(log n) or O(n), are generally more efficient and scalable than those with worse time complexity, such as O(n^2) or O(n!).\n\nBy analyzing the complexity of algorithms, developers can ensure that their software can handle large input sizes without performance issues. This is particularly important in real-world applications, where the amount of data being processed can be significant. Choosing the right algorithm can make the difference between a responsive and efficient application and one that struggles to keep up with user demands.\n\nIn summary, the bubble sort algorithm provides a valuable example for understanding the importance of algorithm analysis and complexity. By studying the time and space complexity of bubble sort, developers can gain insights into the broader concepts of algorithm efficiency and the role it plays in software development.\n\n## Time Complexity Analysis of Bubble Sort\n\n### Introduction to Bubble Sort\'s Time Complexity\n\nBubble sort is a simple sorting algorithm that repeatedly steps through the list, compares adjacent elements, and swaps them if they are in the wrong order. This process continues until the entire list is sorted. While bubble sort is easy to implement, its time complexity is a crucial factor to consider when evaluating its performance and suitability for different applications.\n\n### Worst-Case Time Complexity Analysis\n\nThe worst-case scenario for bubble sort occurs when the input array is in reverse order. In this case, the algorithm must perform the maximum number of comparisons and swaps to sort the array.\n\nIn the first pass, the algorithm will compare and swap (n-1) elements, where n is the size of the input array. In the second pass, it will compare and swap (n-2) elements, and so on. The total number of comparisons can be calculated as the sum of the arithmetic series: (n-1) + (n-2) + (n-3) + ... + 2 + 1 = n(n-1)/2.\n\nSince the number of swaps is equal to the number of comparisons in the worst case, the overall time complexity of bubble sort in the worst-case scenario is O(n^2).\n\n### Best-Case Time Complexity Analysis\n\nThe best-case scenario for bubble sort occurs when the input array is already sorted in ascending order. In this case, the algorithm will only need to perform (n-1) comparisons, with no swaps required, resulting in a time complexity of O(n).\n\nThis best-case scenario is rare in practice, as it requires the input array to be already sorted, which is not a common occurrence. However, it is important to understand the best-case behavior of the algorithm to have a complete picture of its performance characteristics.\n\n### Average-Case Time Complexity Analysis\n\nIn the average case, where the input array is randomly ordered, the time complexity of bubble sort is also O(n^2). This is because the algorithm still needs to perform the same number of comparisons as in the worst-case scenario, with an expected number of swaps being approximately (n-1)/2.\n\nThe average-case time complexity is the same as the worst-case time complexity because the algorithm\'s behavior is not significantly affected by the initial order of the input array. The quadratic time complexity of bubble sort makes it inefficient for large datasets, especially when compared to more advanced sorting algorithms with better average-case performance.\n\n### Big O Notation Explanations\n\nThe time complexity of bubble sort can be expressed using Big O notation as follows:\n\n1. **Worst-case time complexity**: O(n^2)\n   - This occurs when the input array is in reverse order, and the algorithm must perform the maximum number of comparisons and swaps.\n\n2. **Best-case time complexity**: O(n)\n   - This occurs when the input array is already sorted in ascending order, and the algorithm only needs to perform (n-1) comparisons with no swaps.\n\n3. **Average-case time complexity**: O(n^2)\n   - This is the typical case, where the input array is randomly ordered, and the algorithm performs a quadratic number of comparisons and swaps.\n\nThe space complexity of bubble sort is O(1), as it is an in-place sorting algorithm that only requires a constant amount of additional memory for the swap operation.\n\n### Visual Representation of Time Complexity\n\nUnfortunately, the search results did not provide specific visual representations of bubble sort\'s time complexity. However, we can describe how such a visualization might look:\n\nA graph showing the number of comparisons or swaps on the y-axis and the input size on the x-axis would demonstrate a quadratic growth curve for the worst and average cases of bubble sort. This would visually illustrate the algorithm\'s inefficiency as the input size increases, with the number of operations growing much faster than the input size.\n\nAdditionally, an animation or step-by-step visualization of the bubble sort algorithm could show how the number of comparisons decreases in each pass, further reinforcing the understanding of the O(n^2) time complexity.\n\n### Comparison with Other Sorting Algorithms\n\nCompared to more efficient sorting algorithms, such as quicksort, mergesort, and heapsort, which have an average-case time complexity of O(n log n), bubble sort\'s quadratic time complexity makes it less suitable for large datasets. These more advanced algorithms are generally preferred in practice, as they can handle larger input sizes more efficiently.\n\n### Real-World Implications of Bubble Sort\'s Time Complexity\n\nThe poor time complexity of bubble sort, especially in the average and worst cases, makes it impractical for use in most real-world applications that deal with large datasets. The algorithm\'s inefficiency can lead to slow response times, high CPU usage, and even system crashes when dealing with large amounts of data.\n\nAs a result, bubble sort is primarily used as an educational tool to introduce sorting concepts, rather than being employed in production environments. More efficient sorting algorithms are preferred in popular programming languages, as they can handle large-scale data processing tasks more effectively.\n\n## Space Complexity and Implementation Considerations\n\n### Introduction\n\nThe space complexity of sorting algorithms is an important factor to consider, as it determines the memory requirements of the sorting process. Efficient use of memory can be crucial in resource-constrained environments or when dealing with large datasets. In this section, we will explore the space complexity of the bubble sort algorithm, its in-place nature, implementation variations, and the concept of algorithm stability.\n\n### Space Complexity Analysis\n\nBubble sort has a space complexity of O(1), which means it requires a constant amount of additional memory space, regardless of the input size. This is because bubble sort is an in-place sorting algorithm, meaning it modifies the input array directly without the need for additional data structures proportional to the input size.\n\nThe in-place nature of bubble sort can be illustrated with the following pseudocode:\n\n```\nbubbleSort(arr):\n    n = length(arr)\n    for i from 0 to n-1:\n        for j from 0 to n-i-1:\n            if arr[j] > arr[j+1]:\n                swap(arr[j], arr[j+1])\n```\n\nAs shown, bubble sort only uses a few temporary variables for swapping elements, making it a memory-efficient sorting algorithm.\n\n### In-Place Sorting\n\nIn-place sorting algorithms are those that modify the input array directly, without requiring additional memory proportional to the input size. This property makes in-place sorting algorithms, like bubble sort, particularly useful in memory-constrained environments, as they can sort large datasets without the need for extra memory allocation.\n\nThe main advantage of in-place sorting is its efficient use of memory. By operating directly on the input array, in-place algorithms can sort data without the overhead of creating and managing additional data structures, which can be especially beneficial when working with limited memory resources.\n\n### Implementation Variations\n\nThe basic bubble sort algorithm works by repeatedly swapping adjacent elements if they are in the wrong order, until the entire array is sorted. This simple implementation has a time complexity of O(n^2) in the average and worst cases, which can make it inefficient for large datasets.\n\nTo improve the performance of bubble sort, several optimizations have been developed:\n\n1. **Early Termination**: The algorithm can be optimized by stopping the sorting process if no swaps were made during a pass, indicating that the array is already sorted.\n2. **Cocktail Sort**: Also known as bidirectional bubble sort, this variation sorts the array in both directions, alternating between forward and backward passes. This can be more efficient for certain types of partially sorted arrays.\n\nThese optimizations can help reduce the overall time complexity of bubble sort without significantly impacting its space complexity.\n\n### Stability\n\nBubble sort is a stable sorting algorithm, meaning that it preserves the relative order of equal elements in the sorted output. This property is important in certain applications, such as multi-key sorting, where maintaining the original order of equal elements is crucial.\n\nThe stability of bubble sort is a natural consequence of its comparison and swapping mechanism. When two equal elements are compared, they are not swapped, ensuring that their relative order is preserved throughout the sorting process.\n\n### Comparison with Other Algorithms\n\nWhile bubble sort excels in terms of space complexity, with a constant O(1) space requirement, it falls short in time complexity compared to more advanced sorting algorithms like quicksort and mergesort, which have a time complexity of O(n log n).\n\nAlgorithms like mergesort, which have a space complexity of O(n), require additional memory proportional to the input size. In contrast, bubble sort\'s in-place nature makes it more memory-efficient, which can be advantageous in scenarios where memory usage is a primary concern, such as embedded systems or resource-constrained environments.\n\n### Practical Considerations\n\nBubble sort\'s simplicity and in-place nature make it a useful algorithm in certain practical scenarios:\n\n1. **Small Datasets**: For small arrays or nearly sorted data, the simplicity and low overhead of bubble sort can outweigh the performance of more complex algorithms.\n2. **Educational Purposes**: Bubble sort is often used as an educational tool to introduce sorting algorithms and their properties, as its straightforward implementation makes it easy to understand and visualize.\n3. **Parallelization**: Interestingly, bubble sort can be parallelized effectively, potentially reducing its time complexity to O(n) in parallel processing environments, which sets it apart from some other simple sorting algorithms.\n\nWhile more efficient sorting algorithms are generally preferred for large-scale sorting tasks, bubble sort\'s space efficiency and stability can make it a practical choice in specific use cases.\n\n### Conclusion\n\nIn summary, bubble sort\'s space complexity of O(1) and its in-place nature make it a memory-efficient sorting algorithm. Its simplicity and stability also contribute to its usefulness in certain scenarios, such as small datasets, educational purposes, and parallel processing environments. However, the algorithm\'s time complexity of O(n^2) in the average and worst cases limits its practical application for large datasets, where more efficient sorting algorithms like quicksort and mergesort are generally preferred.\n\n## Practical Implications and Comparisons\n\n### Introduction\n\nBubble sort is a simple and intuitive sorting algorithm that has been a staple in computer science education for decades. While it may not be the most efficient algorithm for large-scale applications, it continues to hold relevance in certain practical scenarios and educational contexts. This section explores the real-world applications, limitations, and comparisons of bubble sort, providing a balanced perspective on its place among sorting algorithms.\n\n### Practical Applications of Bubble Sort\n\nDespite its well-known inefficiency for large datasets, bubble sort can still find practical use in specific scenarios. Its simplicity and ease of implementation make it a viable option for organizing small lists or nearly-sorted data.\n\nOne such application is in embedded systems or resource-constrained environments, where the predictability and low memory overhead of bubble sort can be advantageous over more complex algorithms [1]. Additionally, in parallel computing environments, bubble sort can be effectively parallelized, potentially outperforming other sorting algorithms that do not parallelize as well [2].\n\nAnother niche use case for bubble sort is in educational settings. The algorithm\'s step-by-step nature and visual simplicity make it an excellent tool for teaching fundamental sorting concepts and algorithm analysis to students [3]. By understanding the workings of bubble sort, learners can gain valuable insights into the trade-offs between algorithm complexity and performance.\n\n### Limitations and Scenarios to Avoid\n\nWhile bubble sort has its applications, it is generally not recommended for use in modern software development due to its poor performance characteristics. The algorithm\'s worst-case and average-case time complexity of O(n^2) makes it inefficient for large datasets, especially when compared to more advanced sorting algorithms like quicksort and mergesort [4].\n\nIn scenarios involving large or rapidly growing datasets, the performance degradation of bubble sort becomes increasingly problematic. As the input size increases, the time required to sort the data can become unacceptably slow, making bubble sort an unsuitable choice [5].\n\nAdditionally, bubble sort is not recommended for use in applications where the data is already partially sorted. In such cases, algorithms like insertion sort or heapsort can perform significantly better, as they can take advantage of the existing order in the data [6].\n\n### Comparison with Other Sorting Algorithms\n\nWhen compared to other common sorting algorithms, bubble sort stands out for its simplicity but falls short in terms of performance.\n\nQuicksort, for example, has an average-case time complexity of O(n log n), making it significantly more efficient than bubble sort\'s O(n^2) performance. However, quicksort\'s performance is heavily dependent on the choice of the pivot element, and its worst-case scenario can degrade to O(n^2) if the pivot selection is poor [7].\n\nMergesort, on the other hand, maintains a consistent O(n log n) time complexity, regardless of the input data. While it requires additional memory for the merging process, mergesort is a stable sorting algorithm, preserving the relative order of equal elements [8].\n\nSelection sort and insertion sort, like bubble sort, also have a time complexity of O(n^2), but they differ in their implementation and specific use cases. Selection sort is an in-place algorithm, while insertion sort is efficient for partially sorted datasets [9].\n\n### Performance Benchmarks\n\nEmpirical studies have consistently shown that bubble sort significantly underperforms compared to other sorting algorithms, especially as the input size increases. In one benchmark, bubble sort took over 10 seconds to sort 10,000 integers, while more efficient algorithms like counting sort completed the same task in just a few milliseconds [10].\n\nThe performance gap widens as the input size grows, highlighting the importance of selecting the appropriate sorting algorithm for the given problem. While bubble sort may be suitable for small datasets, its quadratic time complexity makes it impractical for large-scale applications.\n\n### Educational Value\n\nDespite its limitations in practical applications, bubble sort remains a valuable tool in computer science education. Its simplicity and intuitive nature make it an excellent introductory algorithm for teaching fundamental sorting concepts and algorithm analysis.\n\nBy understanding the workings of bubble sort, students can gain insights into the importance of algorithm selection, the trade-offs between performance and complexity, and the role of optimization in software development. The step-by-step nature of bubble sort also lends itself well to visualization and hands-on learning, aiding in the comprehension of sorting algorithms [11].\n\nFurthermore, the educational value of bubble sort extends beyond just sorting algorithms. It can be used to illustrate broader computer science concepts, such as the impact of data structures, the importance of algorithm analysis, and the role of empirical performance evaluation in software engineering.\n\n### Conclusion\n\nWhile bubble sort may not be the most efficient sorting algorithm for large-scale applications, it continues to hold relevance in specific practical scenarios and educational contexts. Its simplicity and ease of implementation make it a viable option for organizing small datasets or nearly-sorted data, particularly in resource-constrained environments.\n\nHowever, the algorithm\'s quadratic time complexity renders it unsuitable for large or rapidly growing datasets, where more advanced sorting algorithms like quicksort and mergesort should be preferred. Nonetheless, bubble sort\'s educational value remains strong, as it serves as an excellent introductory tool for teaching fundamental sorting concepts and algorithm analysis.\n\nBy understanding the practical implications, limitations, and comparisons of bubble sort, developers and educators can make informed decisions about when and how to utilize this classic sorting algorithm in their work and teaching practices.\n\n[1] Tavily Search Result 1: "Bubble sort can be applied to various real-life scenarios"\n[2] Tavily Search Result 1: "In parallel computing environments, bubble sort can be parallelized effectively"\n[3] Tavily Search Result 3: "Bubble sort retains relevance as a valuable teaching tool"\n[4] Tavily Search Result 2: "Bubble Sort: Inefficient for large datasets, worst-case time complexity of O(n^2)"\n[5] BraveSearch Search Result 2: Benchmarking data showing bubble sort\'s poor performance for large datasets\n[6] Tavily Search Result 2: "Insertion Sort: Efficient for partially sorted datasets"\n[7] Youtube Search Result 1: "Quicksort\'s performance depends on pivot selection"\n[8] Youtube Search Result 1: "Merge sort is stable, while basic quicksort is not"\n[9] Tavily Search Result 2: Comparison of bubble, selection, and insertion sort properties\n[10] BraveSearch Search Result 2: Benchmarking data showing bubble sort\'s significantly worse performance compared to other algorithms\n[11] ArXiv Search Result 3: "Design Sketch was particularly helpful in enhancing students\' understanding of the abstract concept of \'iteration number\'"\n\n\n## Conclusion\n\nThe comprehensive analysis of the bubble sort algorithm has provided valuable insights into its time and space complexity, as well as its practical implications and comparisons with other sorting algorithms.\n\nRegarding time complexity, the bubble sort algorithm exhibits a worst-case and average-case time complexity of O(n^2), which makes it inefficient for large datasets. This quadratic growth in the number of comparisons and swaps required to sort the input data can lead to unacceptably slow performance as the input size increases. In contrast, the best-case scenario, where the input is already sorted, results in a time complexity of O(n), showcasing the algorithm\'s sensitivity to the initial order of the data.\n\nIn terms of space complexity, bubble sort is an in-place sorting algorithm, requiring only a constant amount of additional memory, O(1), regardless of the input size. This memory-efficient property can be advantageous in resource-constrained environments or when dealing with large datasets that cannot fit entirely in main memory.\n\nWhile the simplicity and stability of bubble sort make it a valuable educational tool, its practical applications are generally limited to small datasets or scenarios where memory usage is a primary concern. In modern software development, more efficient sorting algorithms, such as quicksort and mergesort, with an average-case time complexity of O(n log n), are typically preferred for their superior performance characteristics.\n\nThe analysis of bubble sort\'s time and space complexity highlights the importance of algorithm analysis in software development. By understanding the trade-offs between algorithm efficiency, memory usage, and stability, developers can make informed decisions about which sorting algorithm to use for a given problem, ensuring that their applications can handle large-scale data processing tasks effectively.\n\nAs the field of computer science continues to evolve, the design and selection of algorithms will remain a crucial aspect of software engineering. Emerging trends in algorithm design, such as the development of parallel and distributed sorting algorithms, may further expand the practical applications of sorting algorithms like bubble sort, particularly in the context of high-performance computing and big data processing.\n\nIn conclusion, the analysis of the bubble sort algorithm has provided valuable insights into the fundamental concepts of algorithm complexity and the role it plays in software development. By understanding the strengths, limitations, and practical implications of bubble sort, developers can make more informed choices when selecting sorting algorithms for their applications, ultimately leading to more efficient and scalable software solutions.'}}
        print(result)
        print(f'saved in {task_id}')

        final_result['user_question'] = result['user_question']
        final_result['response'] = result['keys']['generation']
        final_result['document'] = result['keys']['full_documents']

        par_tasks[task_id]['result'] = final_result
        par_tasks[task_id]['status'] = 'completed'
        par_tasks[task_id]['progress'] = 100
        socketio.emit('par_completed', par_tasks[task_id])
    except Exception as e:
        par_tasks[task_id]['status'] = 'error'
        par_tasks[task_id]['error'] = str(e)
        socketio.emit('par_error', {'task_id': task_id, 'error': str(e)})


# @app.route('/start_par', methods=['POST'])
# def start_par():
#     query = request.json.get('query', '')
#     print(f"Starting PAR with query: {query}")
#     task_id = str(uuid.uuid4())  # 고유한 작업 ID 생성
#     par_tasks[task_id] = {
#         'status': 'running',
#         'progress': 0,
#         'query': query,
#         'completed_stages': [],
#         'current_stage': ''
#     }
#
#     # 백그라운드에서 PAR 작업 시작
#     # threading.Thread(target=run_par_task, args=(task_id,)).start()
#     threading.Thread(target=run_async_task, args=(task_id, )).start()
#
#     return jsonify({'task_id': task_id})


@socketio.on('par_input')
def handle_par_input(data):
    task_id = data['task_id']
    user_response = data['response']
    if task_id in par_tasks and par_tasks[task_id].get('awaiting_input'):
        par_tasks[task_id]['user_response'] = user_response
        emit('par_input_received', {'task_id': task_id})


def get_token():
    token_info = session.get('token_info', None)
    print(token_info)
    if token_info:
        # 향후 버전을 위한 호환성 체크
        if isinstance(token_info, str):
            return {'access_token': token_info}

        now = int(time.time())
        is_expired = token_info['expires_at'] - now < 60
        if is_expired:
            sp_oauth.refresh_access_token(token_info['refresh_token'])
            token_info = sp_oauth.get_cached_token()
            session['token_info'] = token_info
    return token_info


@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/logout')
def logout():
    session.pop('token_info', None)
    return redirect(url_for('index'))

@app.route('/callback')
def callback():
    print(f"Received callback from {request.url}: {request.data}, {request.args}")
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code, check_cache=False)

    if isinstance(token_info, dict):
        session['token_info'] = token_info
    else:
        session['token_info'] = {
            'access_token': token_info,
            'expires_at': sp_oauth.get_cached_token()['expires_at']
        }
    return redirect(url_for('index'))


@app.route('/set_device_id', methods=['POST'])
def set_device_id():
    device_id = request.form.get('device_id')
    print(f'device_id: {device_id}')
    session['device_id'] = device_id
    return jsonify({'success': True})


@app.route('/api/play-track', methods=['POST'])
def play_track():
    if 'token_info' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    token_info = session['token_info']
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info

    sp = spotipy.Spotify(auth=token_info['access_token'])

    track_id = request.json['trackId']
    device_id = request.json['deviceId']
    position_ms = request.json.get('position_ms', 0)

    try:
        sp.start_playback(device_id=device_id, uris=[f'spotify:track:{track_id}'], position_ms=position_ms)
        return jsonify({'success': True})
    except spotipy.exceptions.SpotifyException as e:
        return jsonify({'error': str(e)}), 400


@app.route('/par_status/<task_id>')
def par_status(task_id):
    if task_id in par_tasks:
        return jsonify({
            'status': par_tasks[task_id].get('status', 'running'),
            'progress': par_tasks[task_id].get('progress', 0),
            'current_stage': par_tasks[task_id].get('current_stage', ''),
            'completed_stages': par_tasks[task_id].get('completed_stages', []),
            'error': par_tasks[task_id].get('error', ''),
            'awaiting_input': par_tasks[task_id].get('awaiting_input', False),
            'input_data'    : par_tasks[task_id].get('input_data', {})
        })
    return jsonify({'status': 'not found'}), 404


@app.route('/par_input/<task_id>', methods=["POST"])
def par_input(task_id):
    if task_id in par_tasks and par_tasks[task_id].get('awaiting_input'):
        user_response = request.json.get('response')
        par_tasks[task_id]['user_response'] = user_response
        return jsonify({'status': 'input received'})
    return jsonify({'status': 'input not expected'}), 400


def search_tracks(query, search_type='track', offset=0, limit=ITEMS_PER_PAGE):
    if search_type == 'artist':
        results = sp.search(q=query, type='artist', limit=1)
        if results['artists']['items']:
            artist_id = results['artists']['items'][0]['id']
            results = sp.artist_top_tracks(artist_id)
            tracks = results['tracks']
        else:
            return [], 0
    else:
        results = sp.search(q=query, type='track', limit=limit, offset=offset)
        tracks = results['tracks']['items']

    total = len(tracks) if search_type == 'artist' else results['tracks']['total']

    data = []
    for track in tracks:
        artist = track['artists'][0]['name']
        title = track['name']
        album = track['album']['name']
        image_url = track['album']['images'][0]['url'] if track['album']['images'] else 'No Image'

        data.append({
            'id'       : track['id'],
            'artist'   : artist,
            'title'    : title,
            'album'    : album,
            'image_url': image_url,
        })

    return data, total


@app.route('/')
def index():
    token_info = get_token()
    return render_template('index.html', token=token_info['access_token'] if token_info else None)


@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    search_type = request.form['search_type']
    return redirect(url_for('search_results', query=query, search_type=search_type, page=1))


@app.route('/search_results')
def search_results():
    query = request.args.get('query', '')
    search_type = request.args.get('search_type', 'track')
    page = int(request.args.get('page', 1))
    offset = (page - 1) * ITEMS_PER_PAGE

    results, total = search_tracks(query, search_type, offset)
    total_pages = math.ceil(total / ITEMS_PER_PAGE)

    return render_template('results.html',
                           results=results,
                           query=query,
                           page=page,
                           total_pages=total_pages,
                           max=max,
                           min=min)


@app.route('/track/<track_id>')
def get_track_info(track_id):
    track = sp.track(track_id)
    lyrics = "가사를 가져오는 데 실패했습니다."

    print(f"track id: {track_id}")

    print(f"title: {track['name']}")
    print(f"artist: {track['artists'][0]['name']}")

    return jsonify({
        'image_url': track['album']['images'][0]['url'] if track['album']['images'] else '',
        'title'    : track['name'],
        'artist'   : track['artists'][0]['name'],
        'lyrics'   : lyrics
    })


@app.route('/my_library')
def my_library():
    token_info = get_token()
    return render_template('my_library.html', token=token_info['access_token'] if token_info else None)


@app.route('/api/library')
def get_library():
    library_tracks = list(library_collection.find({}, {'_id': 0}))
    return jsonify(library_tracks)


@app.route('/api/library/add', methods=['POST'])
def add_to_library():
    track_id = request.form['track_id']
    track = sp.track(track_id)

    library_track = {
        'id'       : track_id,
        'title'    : track['name'],
        'artist'   : track['artists'][0]['name'],
        'image_url': track['album']['images'][0]['url'] if track['album']['images'] else '',
        'lyrics'   : ''
    }

    print(f"Library_Track: ${library_track}")

    library_collection.update_one({'id': track_id}, {'$set': library_track}, upsert=True)
    return jsonify({'success': True})


@app.route('/api/library/update_lyrics', methods=['POST'])
def update_lyrics():
    track_id = request.form['track_id']
    lyrics = request.form['lyrics']

    result = library_collection.update_one(
        {'id': track_id},
        {
            '$set'  : {'lyrics': lyrics},
            '$unset': {'translated_lyrics': ''}  # 원본 가사가 변경되면 번역된 가사 초기화
        }
    )

    if result.modified_count > 0:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})


@app.route('/api/library/translate', methods=['POST'])
def translate_lyrics():
    track_id = request.form['track_id']
    track = library_collection.find_one({'id': track_id})
    print(track)

    if not track or not track.get('lyrics'):
        return jsonify({'success': False, 'error': 'Lyrics not found'})

    try:
        # TODO(몽고 DB 업데이트 및 텍스트 임베딩 해 벡터 DB 저장까지)
        translated_lyrics = run_translate(track)
        library_collection.update_one({'id': track_id}, {'$set': {'translated_lyrics': translated_lyrics}})

        return jsonify({'success': True, 'translated_lyrics': translated_lyrics})
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return jsonify({'success': False, 'error': 'Translation failed'})


@app.route('/api/library/<track_id>')
def get_track_from_library(track_id):
    track = library_collection.find_one({'id': track_id}, {'_id': 0})
    if track:
        return jsonify(track)
    else:
        return jsonify({'error': 'Track not found'}), 404


@app.route('/api/library/update_translated_lyrics', methods=['POST'])
def update_translated_lyrics():
    track_id = request.form['track_id']
    lyrics = request.form['lyrics']

    result = library_collection.update_one({'id': track_id}, {'$set': {'translated_lyrics': lyrics}})

    if result.modified_count > 0:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})


@app.route('/api/library/regenerate_translation', methods=['POST'])
def regenerate_translation():
    track_id = request.form['track_id']
    track = library_collection.find_one({'id': track_id})

    if not track or not track.get('lyrics'):
        return jsonify({'success': False, 'error': 'Original lyrics not found'})


    try:
        translated_lyrics = run_translate(track)
        library_collection.update_one({'id': track_id}, {'$set': {'translated_lyrics': translated_lyrics}})

        return jsonify({'success': True, 'translated_lyrics': translated_lyrics})
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return jsonify({'success': False, 'error': 'Translation failed'})


@app.route('/web_search')
def web_search():
    query = request.args.get('q', '')
    return render_template('web_search_results.html', query=query)


# New route for Google search API
@app.route('/api/search/google')
def google_search():
    query = request.args.get('q', '')
    # Implement Google search logic here
    # This is a placeholder implementation
    results = [
        {"title": "Google Result 1", "url": "http://example.com/1", "description": "This is the first Google result."},
        {"title": "Google Result 2", "url": "http://example.com/2", "description": "This is the second Google result."},
        {"title": "Google Result 3", "url": "http://example.com/3", "description": "This is the third Google result."}
    ]
    return jsonify(results)

# New route for Tavily search API
@app.route('/api/search/tavily')
def tavily_search():
    query = request.args.get('q', '')
    results = run_tavily_search(query=query)
    return jsonify(results)


# New route for Brave search API
@app.route('/api/search/brave')
def brave_search():
    query = request.args.get('q', '')
    results = run_brave_search(query=query)
    return jsonify(results)


# New route for LLM chat
@app.route('/api/chat', methods=['POST'])
def llm_chat():
    message = request.json.get('message', '')
    # Implement LLM chat logic here
    # This is a placeholder implementation
    response = f"This is a dummy response from the LLM for the message: {message}"
    return jsonify({"response": response})


@app.route('/api/par_results/<task_id>')
def get_par_results(task_id):
    print(f'par results for task {task_id}')
    if task_id in par_tasks:
        return jsonify(par_tasks[task_id])
    else:
        return jsonify({'error': 'Results not found'}), 404


@app.route('/par_search')
def par_search():
    # query = request.args.get('q', '')
    task_id = request.args.get('task_id', '')
    return render_template('par_search_results.html', task_id=task_id)

@app.route('/spotify_player')
def spotify_player():
    token_info = get_token()
    if token_info:
        return render_template('spotify_player.html', token=token_info['access_token'])
    else:
        return "Not authenticated", 401


if __name__ == '__main__':
    app.run(debug=True)


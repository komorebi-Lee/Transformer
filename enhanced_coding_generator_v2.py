# Recovered from enhanced_coding_generator.cpython-310.pyc
# Decompiled v2 at: Tue May 26 22:01:16 2026

def HighQualitySampleLearner():
    logging = <?>
    np = <?>
    Dict = Dict
    List = List
    Any = Any
    Optional = Optional
    Callable = Callable
    Set = Set
    Tuple = Tuple
    re = <?>
    jieba = <?>
    pseg = posseg
    Counter = Counter
    defaultdict = defaultdict

    # ??? LOAD_NAME logging
    # ??? LOAD_NAME __name__
    <?>(<?>.getLogger)
    logger = <?>

        # try:
        Config = Config
        # goto 146
        # ??? LOAD_NAME Exception
        # except matching at 144
        Exception
        Config = None
        # except:
        # goto 146

        raise

        # try:
        CodingLibraryManager = CodingLibraryManager
        # goto 220
        # ??? LOAD_NAME Exception
        # except matching at 218
        Exception
        e = <?>
        # try:

        # ??? LOAD_NAME logger
        # ??? LOAD_NAME e
        <?>("<?>.warningstr('导入CodingLibraryManager失败: ')")
        CodingLibraryManager = None
        # except:
        e = None
        del e
        # goto 220
        e = None
        del e
        raise 

        raise

        # try:
        SemanticMatcher = SemanticMatcher
        # goto 294
        # ??? LOAD_NAME Exception
        # except matching at 292
        Exception
        e = <?>
        # try:

        # ??? LOAD_NAME logger
        # ??? LOAD_NAME e
        <?>("<?>.warningstr('导入SemanticMatcher失败: ')")
        SemanticMatcher = None
        # except:
        e = None
        del e
        # goto 294
        e = None
        del e
        raise 

        raise

        # try:
        RuntimeStrategyDetector = RuntimeStrategyDetector
        RagIndexManager = RagIndexManager
        RAGSemanticMatcher = RAGSemanticMatcher
        FirstLevelClusterer = FirstLevelClusterer
        CodingDecisionPolicy = CodingDecisionPolicy
        CodingDecision = CodingDecision
        # goto 440
        # ??? LOAD_NAME Exception
        # except matching at 438
        Exception
        e = <?>
        # try:

        # ??? LOAD_NAME logger
        # ??? LOAD_NAME e
        <?>("<?>.warningstr('导入RAG组件失败: ')")
        RuntimeStrategyDetector = None
        RagIndexManager = None
        RAGSemanticMatcher = None
        FirstLevelClusterer = None
        CodingDecisionPolicy = None
        CodingDecision = None
        # except:
        e = None
        del e
        # goto 440
        e = None
        del e
        raise 

        raise

        # try:
        HighQualitySampleLearner = HighQualitySampleLearner
        # goto 516
        # ??? LOAD_NAME Exception
        # except matching at 514
        Exception
        e = <?>
        # try:

        # ??? LOAD_NAME logger
        # ??? LOAD_NAME e
        <?>("<?>.warningstr('导入高质量样本学习器失败: ')")
        HighQualitySampleLearner = None
        # except:
        e = None
        del e
        # goto 516
        e = None
        del e
        raise 

        raise
        # def 'EnhancedCodingGenerator'()
        <?>(type, 'EnhancedCodingGenerator')
        EnhancedCodingGenerator = <?>
    return None

class EnhancedCodingGenerator:

    def _clean_code_prefix(code):
        if code: goto 8
        return code
        punctuation_to_remove = '^[。！？，、；：…—·●○◆◇■□▲△▼▽★☆※\\s]+'
        re.sub(punctuation_to_remove, '', code)
        cleaned = <?>
        cleaned.strip()
        return

    def __init__(self):
        5.min_sentence_length = self
        0.6.similarity_threshold = self
        5.max_codes_per_paragraph = self
        if not Config: goto 34
        getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30)
        # goto 36
        30.max_first_level_length = self
        {}.abstract_cache = self
        {}.similarity_cache = self
        ('比如说', '这?种我', '我这种', '然后', '就是说', '还可以$', '^不是', '^就是', '^所以', '^这跳出来了', '^我刚刚说的是', '^我说的是', '^其实', '^那么', '^然后', '^对[，,]?', '^我自己来说的话[，,]?', '^如果说是', '\\[[0-9]+\\]$', '对对$').bad_phrase_patterns = self
        **{'就是把': '将', '就会': '将', '多一点': '增加', '少一点': '减少'}.colloquial_to_formal = self
        1.0.coding_worthy_min_salience = self
        8.coding_worthy_min_length = self
        None.coding_library = self
        if not CodingLibraryManager: goto 710

            # try:
            CodingLibraryManager()
            **'就是为了卖': '以销售为核心'.coding_library = self
            logger.info('编码库管理器初始化成功')
            '就是为了': '旨在'
            # goto 710
            # except matching at 708
            Exception
            e = Exception
            '为了买': '以购买'
            # try:
            logger.error('初始化编码库管理器失败: str(e)')
            '为了买': '以购买'
            # except:
            e = None
            del e
            # goto 710
            e = None
            del e
            raise '为了卖': '以销售'

            raise
            None.semantic_matcher = self
            None.quality_learner = self
            if not HighQualitySampleLearner: goto 882

            # try:
            HighQualitySampleLearner()
            '主要是把': '将'.quality_learner = self
            os = '主要是为了': '旨在'
            os.path.dirname(__file__)
            '主要是做': '从事'(os.path.join, 'csv', 'standard_train_optimized.csv')
            sample_path = '带过来': '引入'
            os.path.exists(sample_path)
            if not '拉来': '引入': goto 808
            self.quality_learner.load_samples(sample_path)
            '聚拢': '吸引'
            logger.info('高质量样本学习器初始化成功')
            '买': '购买'
            # goto 824
            logger.warning('高质量样本文件不存在: str(sample_path)')
            '卖': '销售'
            # goto 882
            # except matching at 880
            Exception
            e = Exception
            '想要': '期望'
            # try:
            logger.error('初始化高质量样本学习器失败: str(e)')
            '想要': '期望'
            # except:
            e = None
            del e
            # goto 882
            e = None
            del e
            raise '想着': '意图'

            raise
            if not SemanticMatcher: goto 966

            # try:
            SemanticMatcher()
            '想知道': '关注'.semantic_matcher = self
            logger.info('语义匹配器初始化成功')
            '觉得': '认为'
            # goto 966
            # except matching at 964
            Exception
            e = Exception
            '讲到': '阐述'
            # try:
            logger.error('初始化语义匹配器失败: str(e)')
            '讲到': '阐述'
            # except:
            e = None
            del e
            # goto 966
            e = None
            del e
            raise {}

            raise
            False.rag_enabled = self
            None.runtime_strategy = self
            None.rag_matcher = self
            None.decision_policy = self
            None.first_level_clusterer = self
            None.rag_index_manager = self
            {}._first_level_trace_meta = self
            {}._second_level_decision_meta = self
            [].first_level_prototypes = self
            self._default_second_threshold()
            **'说到': '提及'.rag_second_level_threshold = self
            self._default_third_threshold()
            '提到': '提及'.rag_third_level_threshold = self
            self._default_cluster_threshold()
            '问到': '询问'.rag_cluster_similarity_threshold = self
            None.rag_doc_retriever = self
            None.knn_abstract_generator = self
            None.t5_generative_coder = self
            None.concept_anchor_index = self
            self._init_rag_components()
            '给到': '提供'
        return None
        '把人': '将人员'
        '有些时候': '偶发情形下'
        '有的时候': '部分情形下'
        '好多时候': '多数情形下'
        '不大': '有限'
        '不怎么': '较少'
        '不太': '不足'
        '不算': '未达'
        '没什么': '缺乏'
        '没办法': '受限'
        '有没有': '是否存在'
        '要不要': '是否需'
        '能不能': '能否'
        {}
        **'是不是': '是否'
        '会不会': '是否'
        '可能是': '可能源于'
        '搞出来': '产出'
        '弄出来': '产出'
        '做出来': '产出'
        '找一下': '排查'
        '看一看': '审视'
        '看一下': '评估'
        '想办法': '寻求方案'
        '更加': '更趋'
        '越来越': '日益'
        '更好的': '优化'
        '就需要': '需'
        '主要是要': '需'
        '变成了': '转化为'
        '会变得': '将转为'
        {}
        **'失去了': '丧失'
        '没有了': '丧失'
        '使得': '促使'
        '造成了': '导致'
        '带来了': '引发'
        '关键是': '关键在于'
        '少部分': '少数'
        '大部分': '多数'
        '基本上': '大体'
        '差不多': '相近'
        '没法': '受限'
        '没有办法': '受限'
        '每次都': '每次均'
        '有时候': '偶尔'
        '经常': '频繁'
        '一点点': '微量'
        '一些': '部分'
        {}
        '好多': '大量'
        '一下子': '骤然'
        '很快': '迅速'
        '慢慢': '逐步'
        '非常': '明显'
        '特别': '显著'
        '总是要': '需持续'
        '总是': '持续'
        '老是': '频繁'
        '不够': '不足'
        '太多': '过多'
        '太难': '困难'
        '很难': '困难'
        '干': '实施'
        '做': '执行'
        '弄': '处理'
        '搞': '开展'
        {}
        []

    def _ensure_first_level_defaults(self):
        hasattr(self, 'abstract_cache')
        if <?>: goto 16
        {}.abstract_cache = self
        hasattr(self, 'max_first_level_length')
        if <?>: goto 48
        if not Config: goto 42
        getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30)
        # goto 44
        30.max_first_level_length = self
        hasattr(self, '_first_level_trace_meta')
        if <?>: goto 64
        {}._first_level_trace_meta = self
        hasattr(self, 'first_level_prototypes')
        if <?>: goto 80
        [].first_level_prototypes = self
        clean_patterns = ('^其实', '^我觉得', '^我认为', '^我感觉', '^如果说', '^然后', '^那么', '^就是说', '\\[[0-9]+\\]$')
        hasattr(self, 'bad_phrase_patterns')

        if not []: goto 130
        isinstance(self.bad_phrase_patterns, list)
        if not <?>: goto 130
        # def 'EnhancedCodingGenerator._ensure_first_level_defaults.<locals>.<genexpr>'()
        any(iter(self.bad_phrase_patterns))
        <?>(<?>)
        if not <?>: goto 144
        list(clean_patterns)
        <?>.bad_phrase_patterns = self
        return None
        return None

    def _default_second_threshold(self):
        if not Config: goto 20
        getattr(Config, 'RAG_SECOND_LEVEL_THRESHOLD', 0.4)
        <?>(float)
        return
        return 0.4

    def _default_third_threshold(self):
        if not Config: goto 20
        getattr(Config, 'RAG_THIRD_LEVEL_THRESHOLD', 0.4)
        <?>(float)
        return
        return 0.4

    def _default_cluster_threshold(self):
        if not Config: goto 20
        getattr(Config, 'RAG_CLUSTER_SIMILARITY_THRESHOLD', 0.76)
        <?>(float)
        return
        return 0.76

    def _clamp_threshold(self, value, default):
        if not (value is None): goto 12
        return default

            # try:
            float(value)
            threshold = <?>
            # goto 52
            # except matching at 50
            Exception
            (TypeError, ValueError)
            # except:
        return default

        raise
        if not (threshold < 0.0): goto 64
        return 0.0
        if not (threshold > 1.0): goto 76
        return 1.0
        return threshold

    def _ensure_rag_threshold_defaults(self):
        hasattr(self, 'rag_second_level_threshold')
        if <?>: goto 20
        self._default_second_threshold()
        <?>.rag_second_level_threshold = self
        hasattr(self, 'rag_third_level_threshold')
        if <?>: goto 40
        self._default_third_threshold()
        <?>.rag_third_level_threshold = self
        hasattr(self, 'rag_cluster_similarity_threshold')
        if <?>: goto 64
        self._default_cluster_threshold()
        <?>.rag_cluster_similarity_threshold = self
        return None
        return None

    def configure_similarity_thresholds(self, second_threshold, third_threshold, cluster_threshold):
        self._ensure_rag_threshold_defaults()

        self._clamp_threshold(second_threshold, self.rag_second_level_threshold)
        <?>.rag_second_level_threshold = self

        self._clamp_threshold(third_threshold, self.rag_third_level_threshold)
        <?>.rag_third_level_threshold = self

        self._clamp_threshold(cluster_threshold, self.rag_cluster_similarity_threshold)
        <?>.rag_cluster_similarity_threshold = self
        if not (self.first_level_clusterer is not None): goto 76
        self.rag_cluster_similarity_threshold.similarity_threshold = self.first_level_clusterer
        self._rebuild_decision_policy_from_matcher()
        return None

    def _apply_similarity_threshold_options(self, coding_thresholds):
        if coding_thresholds: goto 8
        return None
        # def 'EnhancedCodingGenerator._apply_similarity_threshold_options.<locals>.<dictcomp>'()
        (coding_thresholds,)(iter(('second_threshold', 'third_threshold', 'cluster_threshold')))
        threshold_options = <?>
        if not threshold_options: goto 50
        # ??? CALL_FUNCTION_EX 1
        {**{}, **threshold_options}
        return None
        return None
        ()
        self.configure_similarity_thresholds

    def _repair_first_level_sentence_detail(self, sentence):
        if sentence: goto 8 (or pop)
        sentence({})
        detail = dict
        detail.get('content', '')
        if str: goto 48 (or pop)
        detail.get('original_content', '')

        if str: goto 48 (or pop)
        detail.get('text', '')

        <?>(str)
        <?>.strip()
        content = <?>
        if not content: goto 78
        detail.get('content')
        if <?>: goto 78
        content[detail] = 'content'
        if not content: goto 100
        detail.get('original_content')
        if <?>: goto 100
        content[detail] = 'original_content'
        detail.get('sentence_id', '')
        if str: goto 136 (or pop)
        detail.get('code_id', '')

        if str: goto 136 (or pop)
        detail.get('number', '')

        <?>(str)
        <?>.strip()
        <?>.strip('[]')
        sentence_id = <?>
        if sentence_id: goto 196
        re.findall('\\[(\\d+)\\]', content)
        all_markers = <?>
        if not all_markers: goto 196
        sentence_id = all_markers[-1]
        logger.info('从内容中提取最后一个编号 [str(sentence_id)] 作为sentence_id')
        if not sentence_id: goto 294
        re.sub('\\[\\d+\\]', '', content)
        <?>.strip()
        content_clean = <?>
        re.search('^(?:说话人|讲话人)\\s*\\d+$', content_clean)
        if <?>: goto 242
        re.search('^(受访者|采访者|被访者|主持人|采访员|提问者)$', content_clean)
        if not <?>: goto 294
        logger.warning('内容 str(content_clean) 只是说话人标签，移除关联编号 [str(sentence_id)]')
        sentence_id = ''
        detail.pop('sentence_id', None)
        detail.pop('code_id', None)
        if not sentence_id: goto 314
        sentence_id[detail] = 'sentence_id'
        sentence_id[detail] = 'code_id'
        return detail

    def _first_level_anchor_ratio(self, code_text, source_text):
        # def 'EnhancedCodingGenerator._first_level_anchor_ratio.<locals>.<listcomp>'()
        if code_text: goto 14 (or pop)
        code_text('')
        <?>(iter(str))
        code_chars = <?>
        # def 'EnhancedCodingGenerator._first_level_anchor_ratio.<locals>.<genexpr>'()
        if source_text: goto 38 (or pop)
        source_text('')
        set(iter(str))
        <?>(<?>)
        source_chars = <?>
        if code_chars: goto 56
        return 0.0
        # def 'EnhancedCodingGenerator._first_level_anchor_ratio.<locals>.<genexpr>'()
        (source_chars,)(iter(code_chars))
        <?>(sum)
        len(code_chars)
        <?>(max, 1)
        return (<?> / <?>)

    def _is_low_quality_first_level_code(self, code_text, source_text, is_knn):
        if code_text: goto 8 (or pop)
        code_text('')
        str.strip()
        clean = <?>
        if source_text: goto 24 (or pop)
        source_text('')
        str.strip()
        source = <?>
        if clean: goto 40
        return True
        len(clean)
        if not (<?> < 4): goto 56
        return True
        self._looks_semantically_incomplete(clean)
        if not <?>: goto 70
        return True
        self._has_valid_first_level_pos_pattern(clean)
        if <?>: goto 84
        return True
        re.search('^(?:说话人|讲话人)\\s*\\d+$', clean)
        if not <?>: goto 100
        return True
        re.search('^(受访者|采访者|被访者|主持人|采访员|提问者)$', clean)
        if not <?>: goto 116
        return True
        if not Config: goto 138
        getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30)
        # goto 140
        getattr(self, 'max_first_level_length', 30)
        max_len = <?>
        isinstance(max_len, int)
        if not <?>: goto 178
        if not (max_len > 0): goto 178
        len(clean)
        if not (<?> > max_len): goto 178
        return True
        self._is_question_like(clean)
        if not <?>: goto 192
        return True
        re.search('(什么|怎么|哪些|怎么样|如何|哪方面|什么时候|什么程度|什么样)', clean)
        if not <?>: goto 208
        return True
        re.search('(的|了|着|过|到|在|中|和|与|或|并|又|还|也|只|不|没)$', clean)
        if not <?>: goto 234
        self._has_first_level_information_cue(clean)
        if <?>: goto 234
        return True
        re.search('^(这|那|哪|什么|怎么).{0,6}(的|方面|事情|问题|情况|流程|模式|渠道|方法)', clean)
        if not <?>: goto 250
        return True
        re.search('[（(]?\\d{1,2}:\\d{2}[)）]?', clean)
        if not <?>: goto 266
        return True
        re.search('\\[[A-Z]?\\d+\\]', clean)
        if not <?>: goto 282
        return True
        re.search('(没有办法|没办法).*(这个公司|那个时候|因为)', clean)
        if not <?>: goto 298
        return True
        re.search('^(我|我们|你|他|他们)?也?(没有办法|没办法|不知道|不清楚|不确定)', clean)
        if not <?>: goto 314
        return True
        if not ('这个公司' in clean): goto 326
        return True
        re.search('\\u90a3\\u4e2a\\u65f6\\u5019\\u662f\\d+$', clean)
        if not <?>: goto 342
        return True
        re.search('^(后来发现|后来|发现因为|因为他们|因为他|因为我们)', clean)
        if not <?>: goto 358
        return True
        re.search('(后来发现因为|那个时候主要在)', clean)
        if not <?>: goto 374
        return True
        re.search('^(先给您介绍|先给你介绍|先介绍一下|本次访谈|下面介绍)', clean)
        if not <?>: goto 390
        return True
        re.search('^\\D*(?:\\d{1,2}年|\\d{1,2}月份|\\d{1,2}月)', clean)
        if not <?>: goto 416
        self._has_first_level_information_cue(clean)
        if <?>: goto 416
        return True
        re.search('(这块|这一块|那种|这个来做|那个来做)', clean)
        if not <?>: goto 442
        self._has_first_level_information_cue(clean)
        if <?>: goto 442
        return True
        re.search('^(当时|以前|正好|公司原来|我下面|我去做了|我自行|你的|你做|任务一定要|人人的)', clean)
        if not <?>: goto 468
        self._has_first_level_information_cue(clean)
        if <?>: goto 468
        return True
        if not ('那个时候' in clean): goto 490
        self._has_first_level_information_cue(clean)
        if <?>: goto 490
        return True
        re.search('^(因为|所以|但是|不过|然后|如果|其实|就是|那个|这个|后来|当时|我们|我|你|他|他们)', clean)
        if not <?>: goto 522

        re.search('(导致|影响|推动|形成|引入|转变|降低|提高|获得|支持|需求|资源|客户)', clean)
        if <?>: goto 522
        return True
        re.search('(什么的|之类的|那种感觉|这种感觉|这样子|那样子|怎么说呢|就是说|我觉得|相当于|要看|分场合|这个东西|这个事情|这个问题)$', clean)
        if not <?>: goto 540
        return True
        re.search('(我们认为|我认为|我觉得|我觉得应该|我觉得可以|我觉得可能|我觉得会)', clean)
        if not <?>: goto 558
        return True
        re.search('(开始|进行|做了|搞了|弄了|整了)', clean)
        if not <?>: goto 588
        self._has_first_level_information_cue(clean)
        if <?>: goto 588
        return True
        if not ('没有办法直接去借鉴同行业' in source): goto 602
        return True
        len(clean)
        if not (<?> <= 5): goto 632
        self._has_first_level_information_cue(clean)
        if <?>: goto 632
        return True
        if not source: goto 666
        if is_knn: goto 666
        self._first_level_anchor_ratio(clean, source)
        if not (<?> < 0.4): goto 666
        return True
        if not ('您' in clean): goto 692
        self._has_first_level_information_cue(clean)
        if <?>: goto 692
        return True
        re.search('^(是|在|从|对|把|被|让|给|叫|和|与|或|的)', clean)
        if not <?>: goto 736
        len(clean)
        if not (<?> <= 6): goto 736
        self._has_first_level_information_cue(clean)
        if <?>: goto 736
        return True
        clean.startswith('的')
        if not <?>: goto 766
        len(clean)
        if not (<?> <= 8): goto 766
        return True
        re.search('(对不对|是不是|行不行|能不能|有没有|要不要)', clean)
        if not <?>: goto 784
        return True
        re.search('^(以下|以上|这边|那边|前面|后面)', clean)
        if not <?>: goto 802
        return True
        len(clean)
        if not (<?> > 24): goto 836
        clean.count('，')
        if not (<?> >= 1): goto 836
        return True
        re.search('[出对在到各每较\\d]$', clean)
        if not <?>: goto 880
        len(clean)
        if not (<?> <= 8): goto 880
        self._has_first_level_information_cue(clean)
        if <?>: goto 880
        return True
        re.search('(外面|里面|后面|前面|上面|下面)$', clean)
        if not <?>: goto 910
        self._has_first_level_information_cue(clean)
        if <?>: goto 910
        return True
        if not self.quality_learner: goto 948
        self.quality_learner.is_high_quality_like(clean)
        if <?>: goto 948
        logger.debug('编码不符合高质量模式: str(clean)')
        return False

    def _has_first_level_information_cue(self, text):
        if text: goto 8 (or pop)
        text('')
        str.strip()
        t = <?>
        if t: goto 24
        return False

        re.search('(引入|建立|调整|获得|降低|提高|推动|解决|分析|反馈|合作|转变|优化|对接|支持|审批|流程|受影响|受限|不足|短板|导向|循环|机会|需求|资源|服务|监督|指引|开发|探索|协调|整合|压力|风险|保鲜|价值|活动|增长|转型|感知|评价|约束|冲突|规范|惯例|随意|机制|平台|系统|品牌|团队|客户|治理|场景|能力|策略|路径|结构|模式|种植|养殖|加工|收购|销售|土地|农田|灌溉|施肥|收割|品种|产量|品质|有机|绿色|市场|价格|成本|利润|收入|投资|资金|贷款|保险|补贴|税收|消费|购买|供应链|贸易|工艺|手工|技术|传承|培训|制作|原料|工具|设备|标准|质量|检验|认证|生产|优点|好处|优势|缺点|缺陷|问题|关键|核心|重要|主要|根本|本质|特色|亮点|突破|诊疗|康复|护理|患者|医保|药品|临床|公共卫生|健康管理|中医|慢病|教学|课程|师资|学员|教材|职业教育|技能培训|素质教育|在线教育|社区|公益|民生|基层|志愿服务|社区营造|城市更新|旧改|可持续|赋能|非遗|手艺|技艺|传承人|工匠|文创|手工艺|陶艺|织造|雕刻|民俗|古建筑|修缮|文物|文旅|景区|民宿|电商|直播|流量|运营|营销|转化|复购|渠道|粉丝)', t)

        <?>(bool)
        return

    def _looks_semantically_incomplete(self, text):
        if text: goto 8 (or pop)
        text('')
        str.strip()
        t = <?>
        if t: goto 24
        return True
        len(t)
        if not (<?> <= 3): goto 40
        return True
        self._is_question_like(t)
        if not <?>: goto 54
        return True
        re.search('^(因为|所以|但是|不过|然后|如果|就是|其实|那个|这个|后来|当时)$', t)
        if not <?>: goto 70
        return True
        re.search('^(因为|所以|但是|不过|然后|如果|就是|其实|那个|这个|后来|当时)', t)
        if not <?>: goto 96
        self._has_first_level_information_cue(t)
        if <?>: goto 96
        return True
        re.search('(这个|那个|这块|这一块|那种|这种|这样|那样)$', t)
        if not <?>: goto 112
        return True
        re.search('(什么的|之类的)$', t)
        if not <?>: goto 128
        return True
        self._has_first_level_information_cue(t)
        if <?>: goto 154
        len(t)
        if not (<?> <= 6): goto 154
        return True
        re.search('(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$', t)
        if not <?>: goto 180
        self._has_first_level_information_cue(t)
        if <?>: goto 180
        return True
        re.search('(什么|怎么|哪些|怎么样|什么样|如何)', t)
        if not <?>: goto 208
        re.search('(机制|流程|资源|策略|路径|模式|结构|能力|需求|服务|创新|管理|评估|质量|安全|风险)', t)
        if <?>: goto 208
        return True
        re.search('^(是|对|把|被|让|给|从|由|和|与|的)', t)
        if not <?>: goto 246
        len(t)
        if not (<?> <= 6): goto 246
        self._has_first_level_information_cue(t)
        if <?>: goto 246
        return True
        re.search('(的比较|会比较|较为)$', t)
        if not <?>: goto 272
        self._has_first_level_information_cue(t)
        if <?>: goto 272
        return True
        len(t)
        if not (<?> <= 3): goto 298
        self._has_first_level_information_cue(t)
        if <?>: goto 298
        return True
        if not ('您' in t): goto 320
        self._has_first_level_information_cue(t)
        if <?>: goto 320
        return True
        return False

    def _has_valid_first_level_pos_pattern(self, text):
        if text: goto 8 (or pop)
        text('')
        str.strip()
        t = <?>
        if t: goto 24
        return False

            # try:
            # def 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<listcomp>'()
            pseg.cut(t)
            <?>(iter(<?>))
            tokens = <?>
            # goto 70
            # except matching at 68
            Exception
            Exception

            # except:
        return True

        raise
        if tokens: goto 78
        return False
        # def 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<listcomp>'()
        <?>(iter(tokens))
        words = <?>
        # def 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<listcomp>'()
        <?>(iter(tokens))
        flags = <?>
        pronouns = {'他', '他们', '你', '你们', '她', '她们', '它', '它们', '我', '我们'}
        modal_particles = {'么', '吗', '吧', '呀', '呗', '呢', '哈', '哦', '啊', '啦', '嘛', '欸', '诶'}
        weak_starters = {'其实', '后来', '就是', '当时', '然后', '这个', '那个'}
        # def 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<genexpr>'()
        (modal_particles,)(iter(words))
        {}(any)
        if not {}: goto 156
        return False
        # def 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<genexpr>'()
        (pronouns,)(iter(words))
        {}(any)
        if not <?>: goto 182
        return False
        if not words: goto 212
        if not (words[0] in weak_starters): goto 212
        self._has_first_level_information_cue(t)
        if <?>: goto 212
        return False
        # def 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<genexpr>'()
        any(iter(flags))
        <?>(<?>)
        noun_like = <?>
        # def 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<genexpr>'()
        any(iter(flags))
        <?>(<?>)
        verb_like = <?>
        # def 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<genexpr>'()
        any(iter(flags))
        <?>(<?>)
        adj_like = <?>
        if noun_like: goto 274
        return False
        if verb_like: goto 296
        if adj_like: goto 296
        self._has_first_level_information_cue(t)
        if <?>: goto 296
        return False
        return True

    def _contains_colloquial_residue(self, text):
        if text: goto 8 (or pop)
        text('')
        t = str
        re.search('(怎么说呢|就是说|我觉得|相当于|要看|分场合|这个东西|这个事情|这个问题|就是那种|就这种|类似这种)', t)
        if bool: goto 84 (or pop)
        re.search('[吧呢啊嘛呀哦哈哎诶噢呃]', t)

        if bool: goto 84 (or pop)
        re.search('(我的|我们的|你们的|他们的|他的|她的)', t)
        if bool: goto 84 (or pop)
        re.search('(^|[，,、；;])(?:我|我们|你|你们|他|他们|她|她们)(?:也|将|会|跟|和|在|购买|参与|提出|能够|可以|需要|喜欢|已经|当时|就|都|只|要|是|有|不再)', t)
        if bool: goto 84 (or pop)
        re.search('^(然后|就是|所以|但是|不过|其实|那个|这个|后来|当时)', t)
        if bool: goto 84 (or pop)
        re.search('(什么的|之类的|那种感觉|这种感觉|这样子|那样子)$', t)

        <?>(bool)
        return

    def _canonicalize_first_level_candidate_rows(self, candidate_rows, source_text):
        canonical_rows = []
        seen = {}
            # for loop body, delta=270
            row = iter(candidate_rows)
            row.get('text', '')
            if str: goto 36 (or pop)
            str('')
            row.get('knn_source')
            if bool: goto 60 (or pop)
            row.get('anchor_source')
            source_text(bool)
            <?>(<?>, <?>, is_knn,=self._finalize_first_level_candidate)
            canonical = <?>
            if canonical: goto 74

            # goto 12
            dict(row)
            new_row = <?>
            canonical[new_row] = 'text'
            self._conservative_first_level_rank_score(new_row)
            round(float)

            <?>(<?>, 4)
            <?>[new_row] = 'conservative_score'
            seen.get(canonical)
            existing = <?>
            if not (existing is None): goto 156
            len(canonical_rows)
            <?>[seen] = canonical
            canonical_rows.append(new_row)

            # goto 12
            current = canonical_rows[existing]
            float('-inf')
            <?>(new_row.get, 'conservative_score')
            float('-inf')
            <?>(current.get, 'conservative_score')
            if (<?> > <?>): goto 260
            float('-inf')
            <?>(new_row.get, 'conservative_score')
            float('-inf')
            <?>(current.get, 'conservative_score')
            if not (<?> == <?>): goto 268
            float('-inf')
            <?>(new_row.get, 'rule_score')
            float('-inf')
            <?>(current.get, 'rule_score')
            if not (<?> > <?>): goto 268
            new_row[canonical_rows] = existing
            # goto 12
        return canonical_rows

    def _split_first_level_candidate_segments(self, text):
        if text: goto 8 (or pop)
        text('')
        str.strip()
        text = <?>
        if text: goto 24
        return []
        segments = []
        re.split('[。！？!?]+', text)
        sentences = <?>
            # for loop body, delta=122
            sentence = iter(sentences)
            sentence.strip()
            sentence = <?>
            if sentence: goto 62

            # goto 44
            self._extract_semantic_chunks(sentence)
            semantic_chunks = <?>
            if not semantic_chunks: goto 88
            segments.extend(semantic_chunks)
            # goto 44
            re.split('[，,、；;：:\\n\\r]+', sentence)
            parts = <?>
            # def 'EnhancedCodingGenerator._split_first_level_candidate_segments.<locals>.<listcomp>'()
            segments.extend(iter(parts))
            <?>(<?>)
            # goto 44
        return segments

    def _extract_semantic_chunks(self, text):
        chunks = []
        patterns = ('([\\u4e00-\\u9fa5]+[动词]+[\\u4e00-\\u9fa5]+[名词]+[\\u4e00-\\u9fa5]+)', '([\\u4e00-\\u9fa5]+[动词]+[\\u4e00-\\u9fa5]+[名词])', '([\\u4e00-\\u9fa5]+[名词]+[\\u4e00-\\u9fa5]+[动词]+[\\u4e00-\\u9fa5]+[名词])', '([\\u4e00-\\u9fa5]+[形容词]+[\\u4e00-\\u9fa5]+[名词]+[\\u4e00-\\u9fa5]+[名词])')
        verb_list = {'优化', '创新', '协调', '合作', '对接', '建立', '开发', '开展', '引入', '形成', '影响', '探索', '推动', '提高', '支持', '整合', '获得', '解决', '调整', '转变', '追求', '降低'}
        noun_list = {'反馈', '品牌', '团队', '场景', '客户', '平台', '服务', '机制', '模式', '治理', '策略', '系统', '结构', '能力', '资源', '路径', '需求'}

            # try:
            pseg.cut(text)
            {}(list)
            tokens = {}
            len(tokens)
            [](range)
            # for loop body, delta=262
            i = iter(<?>)
            len(tokens)
            (i + 1)((min + 1), (i + 5))
            <?>(<?>, range)
            # for loop body, delta=260
            j = iter(<?>)
            # def 'EnhancedCodingGenerator._extract_semantic_chunks.<locals>.<listcomp>'()
            ''.join(iter(tokens[slice(i, j)]))
            <?>(<?>)
            chunk = <?>
            len(chunk)
            if (<?> < 4): goto 148
            len(chunk)
            if not (<?> > 30): goto 150

            # goto 92
            # def 'EnhancedCodingGenerator._extract_semantic_chunks.<locals>.<listcomp>'()
            <?>(iter(tokens[slice(i, j)]))
            pos_tags = <?>
            # def 'EnhancedCodingGenerator._extract_semantic_chunks.<locals>.<genexpr>'()
            (verb_list,)(iter(tokens[slice(i, j)]))
            <?>(any)
            has_verb = <?>
            # def 'EnhancedCodingGenerator._extract_semantic_chunks.<locals>.<genexpr>'()
            (noun_list,)(iter(tokens[slice(i, j)]))
            <?>(any)
            has_noun = <?>
            if not has_verb: goto 258
            if not has_noun: goto 258
            if not (chunk not in chunks): goto 258
            chunks.append(chunk)
            # goto 92

            # goto 56
        return chunks
            # except matching at 286
            Exception
            Exception

            # except:
        return chunks

        raise

    def _score_first_level_fragment(self, fragment, source_text):
        if fragment: goto 8 (or pop)
        fragment('')
        str.strip()
        clean = <?>
        if clean: goto 28
        float('-inf')
        return
        score = 0.0
        len(clean)
        score(min, 24)
        <?> += (<?> * 0.35)
        score = <?>
        self._is_semantically_complete(clean)
        if not <?>: goto 72
        score += 2.0
        score = <?>
        self._first_level_anchor_ratio(clean, source_text)
        <?> += (score * 3.0)
        score = <?>
        re.search('^(追求|引入|建立|调整|获得|降低|提高|推动|解决|客户|越轨|创新|资源|需求|反馈|开展|优化|合作|转变|对接|影响)', clean)
        if not <?>: goto 112
        score += 1.0
        score = <?>
        if not self.quality_learner: goto 162
        self.quality_learner.score_by_pattern_match(clean)
        quality_score = <?>
        score += (quality_score * 0.3)
        score = <?>
        self.quality_learner.is_high_quality_like(clean)
        if <?>: goto 162
        score -= 0.5
        score = <?>
        clean.startswith(('我觉得', '其实', '然后', '所以', '但是', '不过', '当时', '那个时候', '就是', '相当于', '要看', '分场合', '我们', '我', '你', '他', '他们'))
        if not <?>: goto 180
        score -= 1.0
        score = <?>
        self._contains_colloquial_residue(clean)
        if not <?>: goto 198
        score -= 2.0
        score = <?>
        re.search('(这个东西|这个事情|这个问题|什么的|之类的)$', clean)
        if not <?>: goto 218
        score -= 2.5
        score = <?>
        self._has_first_level_information_cue(clean)
        if not <?>: goto 236
        score += 1.2
        score = <?>
        re.search('(受影响|受限|受阻|不足|短板|风险|压力|冲突)', clean)
        if not <?>: goto 256
        score += 0.8
        score = <?>
        self._has_first_level_information_cue(text)
        if not <?>: goto 274
        score += 1.2
        score = <?>
        re.search('(反馈|诉求|需求|受影响|短板|机会)', text)
        if not <?>: goto 294
        score += 0.8
        score = <?>
        re.search('(主要负责|指引方向|监督结果|我们认为|我认为|我觉得)', text)
        if not <?>: goto 314
        score -= 0.7
        score = <?>
        return score

    def _finalize_first_level_candidate(self, text, source_text, is_knn):
        if text: goto 16 (or pop)
        text('')
        self._normalize_candidate_for_first_level(str)

        <?>(self.rewrite_first_level_code)
        candidate = <?>
        bool(source_text)
        if not <?>: goto 66 (or pop)
        if candidate: goto 40 (or pop)
        candidate('')
        str.strip()
        getattr(self, 'first_level_recall_bank', [])
        if set: goto 62 (or pop)
        set([])
        is_recall_label = (<?> in <?>)
        if is_recall_label: goto 74 (or pop)
        is_external = is_knn
        if candidate: goto 84
        return ''
        len(candidate)
        if not (is_recall_label < 4): goto 104
        if is_external: goto 104
        return ''
        len(candidate)
        if not (<?> <= 5): goto 134
        self._has_first_level_information_cue(candidate)
        if <?>: goto 134
        if is_external: goto 134
        return ''
        re.search('(什么|怎么|哪些|怎么样|如何|哪方面|什么时候|什么样)', candidate)
        if not <?>: goto 150
        return ''
        self._contains_colloquial_residue(candidate)
        if <?>: goto 218
        if is_external: goto 180
        self._is_low_quality_first_level_code(candidate, source_text, is_knn,=is_knn)
        if <?>: goto 218
        self._formalize_code(candidate)
        formalized = <?>
        len(formalized)
        if not (<?> >= 4): goto 218
        re.search('(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$', formalized)
        if <?>: goto 218
        return formalized
        best_fragment = ''
        float('-inf')
        best_score = <?>
        self._split_first_level_candidate_segments(candidate)
            # for loop body, delta=434
            fragment = iter(<?>)
            self._normalize_candidate_for_first_level(fragment)
            <?>(self.rewrite_first_level_code)
            refined = <?>
            if refined: goto 266

            # goto 240
            len(refined)
            if not (<?> < 4): goto 304
            getattr(self, 'first_level_recall_bank', [])
            if set: goto 296 (or pop)
            set([])
            if not (<?> not in refined): goto 304

            # goto 240
            len(refined)
            if not (<?> <= 5): goto 352
            self._has_first_level_information_cue(refined)
            if <?>: goto 352
            getattr(self, 'first_level_recall_bank', [])
            if set: goto 344 (or pop)
            set([])
            if not (<?> not in refined): goto 352

            # goto 240
            self._contains_colloquial_residue(refined)
            if not <?>: goto 364

            # goto 240
            self._is_question_like(refined)
            if not <?>: goto 376

            # goto 240
            re.search('(什么|怎么|哪些|怎么样)', refined)
            if not <?>: goto 390

            # goto 240
            self._is_low_quality_first_level_code(refined, source_text)
            if not <?>: goto 404

            # goto 240
            self._score_first_level_fragment(refined, source_text)
            score = <?>
            if not (score > best_score): goto 432
            best_score = score
            best_fragment = refined
            # goto 240
            if not best_fragment: goto 532
            len(best_fragment)
            if not (<?> > 20): goto 458
            threshold = 7.5
            # goto 480
            len(best_fragment)
            if not (<?> < 8): goto 476
            threshold = 6.5
            # goto 480
            threshold = 5.5
            if not (best_score >= threshold): goto 532
            self._formalize_code(best_fragment)
            formalized = <?>
            len(formalized)
            if not (<?> >= 4): goto 532
            re.search('(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$', formalized)
            if <?>: goto 532
        return formalized
        return ''

    def _conservative_first_level_rank_score(self, row):
        row.get('text', '')
        if str: goto 20 (or pop)
        str('')
        row.get('source_text', '')
        if str: goto 38 (or pop)
        str('')
        <?>(<?>, self._finalize_first_level_candidate)
        text = <?>
        if text: goto 56
        float('-inf')
        return
        row.get('rerank_score')
        rerank_score = <?>
        if not (rerank_score is not None): goto 82
        float(rerank_score)
        # goto 84
        model_score = 0.0
        row.get('rule_score', 0.0)
        if float: goto 102 (or pop)
        float(0.0)
        rule_score = <?>
        row.get('semantic_recall_score', 0.0)
        if float: goto 122 (or pop)
        float(0.0)
        recall_score = <?>
        min(rule_score, 6.0)
        score = (<?> + ((model_score * 10.0) * 0.25))
        if not Config: goto 298
        getattr(Config, 'FIRST_LEVEL_FUSED_RANKING', False)
        if not <?>: goto 298
        min(recall_score, 2.0)
        getattr(Config, 'FIRST_LEVEL_RECALL_SCORE_WEIGHT', 1.8)
        score(float)
        <?> += (<?> * <?>)
        score = <?>
        max(rule_score, 0.0)
        score(min, 10.0)
        getattr(Config, 'FIRST_LEVEL_RULE_SCORE_WEIGHT', 0.18)
        <?>(float)
        <?> += (<?> * <?>)
        score = <?>
        row.get('semantic_recall_score')
        if not (<?> is not None): goto 252
        score += 0.8
        score = <?>
        row.get('semantic_recall_score')
        if not (<?> is not None): goto 298
        len(text)
        if not (<?> <= 8): goto 298
        getattr(Config, 'FIRST_LEVEL_SHORT_LABEL_BONUS', 2.5)
        score(float)
        <?> += <?>
        score = <?>
        text.count('，')
        <?> -= (score * 1.25)
        score = <?>
        len(text)
        score(max, (0 - 22))
        <?> -= (<?> * 0.18)
        score = <?>
        len(text)
        score(max, (0 - 30))
        <?> -= (<?> * 0.55)
        score = <?>
        re.search('^(时候|比如|然后|所以|那没有|会，因为|他们有时候|我们有时候)', text)
        if not <?>: goto 388
        score -= 2.5
        score = <?>
        re.search('(\\u8fd9\\u4e2a\\u4e8b\\u60c5|\\u8fd9\\u4e00\\u5757\\u76ee\\u524d\\u6211\\u4eec\\u80fd\\u591f|\\u90a3\\u4e2a\\u65f6\\u5019)', text)
        if not <?>: goto 408
        score -= 1.8
        score = <?>
        re.search('^(我们|他们|你们|大家|这个|那个|这种|这些|那些|他是|我是|你是)', text)
        if not <?>: goto 428
        score -= 1.4
        score = <?>
        re.search('(技术|品牌|资源|平台|机制|流程|生态|需求|问题|合作|协同|创新|服务|应用|模块|设备|系统|客户|团队|工业互联网)', text)
        if not <?>: goto 460
        len(text)
        if not (<?> <= 16): goto 460
        score += 0.7
        score = <?>
        return score

    def _model_semantic_similarity(self, a, b):
        if self.semantic_matcher: goto 10
        return -1.0

            # try:
            getattr(self.semantic_matcher, 'get_embedding', None)
            emb_fn = <?>
            if emb_fn: goto 36
        return -1.0
        emb_fn(a)
        emb_a = <?>
        emb_fn(b)
        emb_b = <?>
        if (emb_a is None): goto 68
        if not (emb_b is None): goto 74
        return -1.0
        np.dot(emb_a, emb_b)
        np.linalg.norm(emb_a)
        np.linalg.norm(emb_b)
        <?>((<?> / ((<?> * float) + 1e-12)))
        return
            # except matching at 138
            Exception
            Exception

            # except:
        return -1.0

        raise

    def _select_quality_first_level_candidate(self, trace, source_detail):
        source_detail.get('original_content', '')
        if str: goto 36 (or pop)
        source_detail.get('content', '')

        if str: goto 36 (or pop)
        source_detail.get('text', '')

        <?>(str)
        source_text = <?>
        trace.get('selected_candidate', '')
        if str: goto 60 (or pop)
        str('')

        <?>(self._finalize_first_level_candidate, source_text)
        selected = <?>
        if not selected: goto 100
        self._is_low_quality_first_level_code(selected, source_text)
        if <?>: goto 100
        self._validate_code_semantic_fit(selected, source_text)
        if not <?>: goto 100
        return selected
        trace.get('candidates', [])
        <?>(list)
        rows = <?>
        # def 'EnhancedCodingGenerator._select_quality_first_level_candidate.<locals>.<lambda>'()
        <?>(key=rows.sort, reverse=True)
            # for loop body, delta=250
            row = iter(rows)
            row.get('text', '')
            if str: goto 162 (or pop)
            str('')

            <?>(self._finalize_first_level_candidate, source_text)
            candidate = <?>
            if not candidate: goto 248
            self._is_low_quality_first_level_code(candidate, source_text)
            if <?>: goto 248
            self._validate_code_semantic_fit(candidate, source_text)
            if not <?>: goto 248
            candidate[trace] = 'selected_candidate'
            # for loop body, delta=240
            candidate_row = iter(rows)
            candidate_row.get('text')
            row.get('text')
            (<?> == <?>)[candidate_row] = 'selected'
            # goto 210
            candidate
        return
        # goto 138
        return ''

    def _validate_code_semantic_fit(self, code, source_text):
        if not code: goto 8
        if source_text: goto 12
        return True
        self._model_semantic_similarity(code, source_text)
        sim = <?>
        if not (sim < 0): goto 36
        return True
        if not (sim < 0.3): goto 74
        "模型语义验证拒绝: '"("str(code) 与原文语义关联过弱 (simformat('.3f'))")
        logger.info
        return False
        if not (sim > 0.96): goto 112
        "模型语义验证拒绝: '"("str(code) 与原文几乎相同，未完成抽象 (simformat('.3f'))")
        logger.info
        return False
        return True

    def _score_first_level_fragment(self, fragment, source_text):
        if fragment: goto 8 (or pop)
        fragment('')
        str.strip()
        clean = <?>
        if clean: goto 28
        float('-inf')
        return
        score = 0.0
        len(clean)
        score(min, 24)
        <?> += (<?> * 0.35)
        score = <?>
        self._is_semantically_complete(clean)
        if not <?>: goto 72
        score += 2.0
        score = <?>
        self._first_level_anchor_ratio(clean, source_text)
        <?> += (score * 3.0)
        score = <?>
        self._has_first_level_information_cue(clean)
        if not <?>: goto 110
        score += 1.2
        score = <?>
        re.search('(反馈|诉求|需求|受影响|短板|机会)', clean)
        if not <?>: goto 130
        score += 0.8
        score = <?>
        re.search('^(追求|引入|建立|调整|获得|降低|提高|推动|解决|客户|越轨|创新|资源|反馈|开展|优化|合作|转变|对接|影响|分析)', clean)
        if not <?>: goto 150
        score += 1.0
        score = <?>
        clean.startswith(('我觉得', '其实', '然后', '所以', '但是', '不过', '当时', '那个时候', '就是', '相当于', '要看', '分场合', '后来', '以前因为', '当我'))
        if not <?>: goto 168
        score -= 2.0
        score = <?>
        self._contains_colloquial_residue(clean)
        if not <?>: goto 186
        score -= 3.0
        score = <?>
        re.search('(这个东西|这个事情|这个问题|这块|这一块|那种)$', clean)
        if not <?>: goto 206
        score -= 2.0
        score = <?>
        re.search('(主要负责|指引方向|监督结果)', clean)
        if not <?>: goto 226
        score -= 0.7
        score = <?>
        return score

    def _conservative_first_level_rank_score(self, row):
        row.get('knn_source')
        <?>(bool)
        _knn = <?>
        row.get('text', '')
        if str: goto 34 (or pop)
        str('')
        <?>(self._finalize_first_level_candidate, is_knn,=_knn)
        text = <?>
        if text: goto 56
        float('-inf')
        return
        row.get('rerank_score')
        rerank_score = <?>
        if not (rerank_score is not None): goto 82
        float(rerank_score)
        # goto 84
        model_score = 0.0
        row.get('rule_score', 0.0)
        if float: goto 102 (or pop)
        float(0.0)
        rule_score = <?>
        min(rule_score, 12.0)
        score = (<?> + ((model_score * 6.0) * 0.5))
        row.get('source_text', '')
        if str: goto 144 (or pop)
        str('')
        source_text = <?>
        if not source_text: goto 272
        re.search('(不|没有|无需|从未|并未|毫不)', source_text)
        if not <?>: goto 272
        re.search('(不|没有|无需|从未|并未|毫不)', text)
        if <?>: goto 272
        re.finditer('(不|没有|无需|从未|并未|毫不)(.{1,10})', source_text)
            # for loop body, delta=272
            m = iter(<?>)
            m.group(2)
            positive_part = <?>
            len(positive_part)
            if not (<?> >= 2): goto 270
            # def 'EnhancedCodingGenerator._conservative_first_level_rank_score.<locals>.<genexpr>'()
            (positive_part,)(iter(text))
            <?>(sum)
            common = <?>
            len(text)
            common((min * 0.5), 3)
            if not (<?> >= <?>): goto 270
            score -= 5.0
            score = <?>
            # goto 272
            # goto 188
            semantic_cues = '(优点|好处|优势|缺点|缺陷|问题|关键|核心|重要|主要|根本|本质|特色|亮点|突破|创新)'
            if not source_text: goto 312
            re.search(semantic_cues, source_text)
            if not <?>: goto 312
            re.search(semantic_cues, text)
            if not <?>: goto 312
            score += 2.5
            score = <?>
            row.get('prototype_hits')
            if <?>: goto 324 (or pop)
            prototype_hits = []
            if not prototype_hits: goto 366
            # def 'EnhancedCodingGenerator._conservative_first_level_rank_score.<locals>.<genexpr>'()
            max(iter(prototype_hits))
            <?>(<?>)
            best_similarity = <?>
            min(2.2, (best_similarity * 3.0))
            <?> += score
            score = <?>
            row.get('semantic_recall_score', 0.0)
            if float: goto 382 (or pop)
            float(0.0)
            recall_score = <?>
            if not (recall_score > 0): goto 412
            min(1.8, (recall_score * 2.0))
            <?> += score
            score = <?>
            row.get('knn_score', 0.0)
            if float: goto 428 (or pop)
            float(0.0)
            knn_score_val = <?>
            row.get('knn_source')
            if not <?>: goto 466
            if not (knn_score_val > 0): goto 466
            score += (3.5 + (knn_score_val * 3.0))
            score = <?>
            text.count('，')
            <?> -= (score * 1.0)
            score = <?>
            len(text)
            score(max, (0 - 28))
            <?> -= (<?> * 0.12)
            score = <?>
            len(text)
            score(max, (0 - 36))
            <?> -= (<?> * 0.4)
            score = <?>
            re.search('^(时候|比如|然后|所以|那没有|会，因为|他们有时候|我们有时候|后来|以前因为|当我)', text)
            if not <?>: goto 558
            score -= 2.5
            score = <?>
            re.search('(\\u8fd9\\u4e2a\\u4e8b\\u60c5|\\u8fd9\\u4e00\\u5757\\u76ee\\u524d\\u6211\\u4eec\\u80fd\\u591f|\\u90a3\\u4e2a\\u65f6\\u5019|这块|这一块|那种)', text)
            if not <?>: goto 580
            score -= 1.8
            score = <?>
            re.search('^(追求|引入|建立|调整|获得|降低|提高|推动|解决|客户|越轨|创新|资源|需求|反馈|分析)', text)
            if not <?>: goto 602
            score += 0.8
            score = <?>
            re.search('^(我们|他们|你们|大家|这个|那个|这种|这些|那些|他是|我是|你是|一开始)', text)
            if not <?>: goto 624
            score -= 1.4
            score = <?>
            row.get('compressed_variant')
            if not <?>: goto 658
            re.search('(我|我们|你|你们|他|他们|这个|那个)', text)
            if <?>: goto 658
            score += 1.1
            score = <?>
            re.search('(技术|品牌|资源|平台|机制|流程|生态|需求|问题|合作|协同|创新|服务|应用|模块|设备|系统|客户|团队|工业互联网)', text)
            if not <?>: goto 694
            len(text)
            if not (<?> <= 16): goto 694
            score += 0.7
            score = <?>
            self._has_first_level_information_cue(text)
            if not <?>: goto 714
            score += 1.2
            score = <?>
            re.search('(反馈|诉求|需求|受影响|短板|机会)', text)
            if not <?>: goto 736
            score += 0.8
            score = <?>
            re.search('(主要负责|指引方向|监督结果)', text)
            if not <?>: goto 758
            score -= 0.7
            score = <?>
        return score

    def _rebuild_decision_policy_from_matcher(self):
        if not CodingDecisionPolicy: goto 10
        if self.rag_matcher: goto 14
        return None
        if not self.rag_matcher: goto 30
        self.rag_matcher.second_code_name_map()
        # goto 32
        second_name_map = {}
        if not self.rag_matcher: goto 50
        self.rag_matcher.third_level_name_map()
        # goto 52
        third_name_map = {}
        second_name_map.keys()
        self.rag_third_level_threshold(list)
        third_name_map.keys()
        self.rag_second_level_threshold(list)
        <?>(second_threshold=<?>, third_threshold=<?>, allowed_second_code_ids=<?>, allowed_third_level_ids=CodingDecisionPolicy, allowed_second_code_names=second_name_map, allowed_third_level_names=third_name_map)
        <?>.decision_policy = self
        return None

    def set_first_level_prototypes(self, prototypes):
        # def 'EnhancedCodingGenerator.set_first_level_prototypes.<locals>.<listcomp>'()
        if prototypes: goto 12 (or pop)
        prototypes(iter([]))
        <?>.first_level_prototypes = self
        return None

    def set_first_level_recall_bank(self, labels, model_manager):
        self._ensure_first_level_defaults()
        unique_labels = []
        set()
        seen = <?>
        if labels: goto 24 (or pop)
            # for loop body, delta=82
            label = iter([])
            if label: goto 38 (or pop)
            label('')
            str.strip()
            text = labels
            if not text: goto 58
            if not (text in seen): goto 60

            # goto 26
            seen.add(text)
            unique_labels.append(text)
            # goto 26
            unique_labels.first_level_recall_bank = self
            None.first_level_recall_embeddings = self
            if not (model_manager is not None): goto 156
            if not unique_labels: goto 160

            # try:
            model_manager.get_embeddings(unique_labels, model_type,='sentence')
            <?>.first_level_recall_embeddings = self
        return None
            # except matching at 154
            Exception
            Exception
            None.first_level_recall_embeddings = self
            # except:
        return None

        raise
        return None
        return None

    def _semantic_recall_first_level_labels(self, text, model_manager, top_n, min_score):
        self._ensure_first_level_defaults()
        getattr(self, 'first_level_recall_bank', [])
        if <?>: goto 22 (or pop)
        labels = []
        if labels: goto 32
        return []
        # def 'EnhancedCodingGenerator._semantic_recall_first_level_labels.<locals>.lexical_hits'()
        lexical_hits = (labels, text, top_n)
        if not (model_manager is None): goto 80
        lexical_hits()
        return ('return', List[Dict[(str, Any)]])

            # try:
            getattr(self, 'first_level_recall_embeddings', None)
            label_embs = <?>
            if not (label_embs is None): goto 122
            model_manager.get_embeddings(labels, model_type,='sentence')
            label_embs = <?>
            label_embs.first_level_recall_embeddings = self
            if (label_embs is None): goto 142
            len(label_embs)
            if not (<?> == 0): goto 150
            lexical_hits()
        return
        model_manager.get_embeddings([text], model_type,='sentence')
        query_emb = <?>[0]
        np.linalg.norm(query_emb)
        q_norm = <?>
        np.linalg.norm(label_embs, axis,=1)
        l_norms = <?>
        np.maximum((q_norm * l_norms), 1e-12)
        denom = <?>
        np.dot(label_embs, query_emb)
        sims = (<?> / denom)
        np.argsort(-(sims))
        int(top_n)
        None(max, 1)
        order = <?>[slice(<?>, <?>)]
        results = []
            # for loop body, delta=322
            idx = iter(order)
            float(sims[idx])
            score = <?>
            if not (score < min_score): goto 294

            # goto 268
            int(idx)
            <?>({'text': results.append[labels], 'score': score, 'recall_type': 'semantic'})
            # goto 268
            if results: goto 330 (or pop)
            lexical_hits()
        return results
            # except matching at 356
            Exception
            Exception
            lexical_hits()
            # except:
        return

        raise

    def _prototype_keywords(self, manual_code):
        if manual_code: goto 8 (or pop)
        manual_code('')
        manual = str
        # def 'EnhancedCodingGenerator._prototype_keywords.<locals>.<setcomp>'()
        jieba.lcut(manual)
        <?>(iter(<?>))
        words = <?>
        if ('客户需求' in manual): goto 48
        if not ('需求导向' in manual): goto 62
        {}({'买', '卖', '客户', '要', '需求'})
        words.update
        if not ('反馈' in manual): goto 84
        {}({'反馈', '客户', '诉求'})
        words.update
        if not ('沟通' in manual): goto 106
        {}({'信任', '推销', '沟通'})
        words.update
        return words

    def _prototype_similarity(self, text, prototype):
        # def 'EnhancedCodingGenerator._prototype_similarity.<locals>.<genexpr>'()
        if text: goto 20 (or pop)
        text('')
        jieba.lcut(str)
        <?>(iter(set))
        <?>(<?>)
        text_tokens = <?>
        # def 'EnhancedCodingGenerator._prototype_similarity.<locals>.<genexpr>'()
        prototype.get('source', '')
        jieba.lcut(str)
        <?>(set)
        <?>(iter(<?>))
        <?>(<?>)
        source_tokens = <?>
        prototype.get('manual_first_code', '')
        self._prototype_keywords(str)
        <?>(<?>)
        manual_tokens = <?>
        if text_tokens: goto 98
        return 0.0
        len((text_tokens & source_tokens))
        len(text_tokens)
        len(source_tokens)
        max(1, min)
        <?>(<?>, <?>)
        source_overlap = (<?> / <?>)
        len((text_tokens & manual_tokens))
        len(manual_tokens)
        <?>(max, 1)
        manual_overlap = (<?> / <?>)
        return ((0.75 * source_overlap) + (0.25 * manual_overlap))

    def _find_first_level_prototype_hits(self, text, top_k):
        self._ensure_first_level_defaults()
        scored = []
            # for loop body, delta=90
            prototype = iter(self.first_level_prototypes)
            self._prototype_similarity(text, prototype)
            score = <?>
            if not (score <= 0): goto 44

            # goto 18
            prototype.get('source', '')
            prototype.get('manual_first_code', '')
            float(score)
            scored.append(round, 4)

            <?>({'source': <?>, 'manual_first_code': <?>, 'similarity': <?>})
            # goto 18
            # def 'EnhancedCodingGenerator._find_first_level_prototype_hits.<locals>.<lambda>'()
            <?>(key=scored.sort, reverse=True)
        return scored[slice(None, top_k)]

    def reset_first_level_trace_meta(self):
        self._ensure_first_level_defaults()
        {}._first_level_trace_meta = self
        return None

    def get_first_level_trace_meta(self):
        self._ensure_first_level_defaults()
        dict(self._first_level_trace_meta)
        return

    def _store_first_level_trace(self, code_key, trace):
        self._ensure_first_level_defaults()
        trace.get('selected_candidate', '')
        trace.get('best_rule_candidate', '')
        trace.get('used_rerank', False)
        <?>(bool)
        trace.get('prototype_enabled', False)
        <?>(bool)
        trace.get('prototype_hits', [])
        <?>(list)
        # def 'EnhancedCodingGenerator._store_first_level_trace.<locals>.<listcomp>'()
        trace.get('candidates', [])
        <?>(iter(<?>))
        compact_trace = {'selected_candidate': <?>, 'best_rule_candidate': <?>, 'used_rerank': <?>, 'prototype_enabled': <?>, 'prototype_hits': <?>, 'candidates': <?>}
        compact_trace[self._first_level_trace_meta] = code_key
        return None

    def build_first_level_candidate_trace(self, sentence, model_manager, top_n, defer_rerank):
        self._ensure_first_level_defaults()
        if sentence: goto 14 (or pop)
        ''.strip()
        original = sentence
        if original: goto 46
        return {'original_sentence': '', 'normalized_sentence': '', 'selected_candidate': '', 'best_rule_candidate': '', 'used_rerank': False, 'prototype_enabled': False, 'prototype_hits': [], 'candidates': []}
        re.sub('^(?:[A-Za-z]|\\u7b54|\\u53d7\\u8bbf\\u8005|\\u88ab\\u8bbf\\u8005)[:\\uFF1A\\s]*', '', original)
        normalized = <?>

        _speaker_label = '(?:\\u53d7\\u8bbf\\u8005|\\u91c7\\u8bbf\\u8005|\\u8bbf\\u8c08\\u5458|\\u8bf4\\u8bdd\\u4eba\\s*\\d+|\\u91cc\\u5f04\\u7ba1\\u5bb6\\s*\\d*|\\u6e38\\u5ba2\\s*\\d*|\\u975e\\u9057\\u624b\\u827a\\u4eba\\s*\\d*|\\u975e\\u9057\\u4eba\\s*\\d*|\\u7ba1\\u7406\\u5c42\\s*\\d*|\\u666f\\u6f02\\s*\\d*|\\u8001\\u5e08\\s*\\d*|\\u4e3b\\u6301\\u4eba|\\u8bb0\\u8005|\\u88ab\\u8bbf\\u8005|\\u5609\\u5bbe|\\u4e13\\u5bb6|\\u5c45\\u6c11\\s*\\d*|\\u5546\\u6237\\s*\\d*|\\u624b\\u827a\\u4eba\\s*\\d*|\\u5b66\\u5f92\\s*\\d*|\\u4f20\\u627f\\u4eba\\s*\\d*|\\u95ee|\\u7b54|Q|A)'
        re.sub('^str(_speaker_label)\\\\s*[\\\\uFF1A:]?\\\\s*', '', normalized)
        normalized = <?>
        re.sub('\\[[A-Z]?\\d+\\]', '', normalized)
        normalized = <?>
        re.sub('(\\w)\\1{2,}', '\\1', normalized)
        normalized = <?>
        self._normalize_source_sentence(normalized)
        normalized = <?>
        if normalized: goto 150
        return {'original_sentence': original, 'normalized_sentence': '', 'selected_candidate': '', 'best_rule_candidate': '', 'used_rerank': False, 'prototype_enabled': False, 'prototype_hits': [], 'candidates': []}
        self._find_first_level_prototype_hits(normalized)
        prototype_hits = <?>
        set()
        prototype_keywords = <?>
            # for loop body, delta=200
            hit = iter(prototype_hits)
            hit.get('manual_first_code', '')
            prototype_keywords.update(self._prototype_keywords)
            <?>(<?>)
            # goto 170
            self._compute_salience(normalized)
            salience = <?>
            rag_context_terms = []
            hasattr(self, 'rag_doc_retriever')
            if not <?>: goto 332
            if not (self.rag_doc_retriever is not None): goto 332

            # try:
            self.rag_doc_retriever.retrieve(normalized, top_k=3, min_score=0.5)
            rag_chunks = <?>
            # for loop body, delta=292
            chunk = iter(rag_chunks)
            chunk.get('text', '')
            <?>(self._extract_domain_terms_from_text)
            chunk_terms = <?>
            rag_context_terms.extend(chunk_terms)
            # goto 258
            if not rag_context_terms: goto 310
            dict.fromkeys(rag_context_terms)
            <?>(list)
            rag_context_terms = <?>
            # goto 332
            # except matching at 330
            Exception
            Exception

            # except:
            # goto 332

            raise
            self._should_skip_sentence_for_coding(normalized, salience)
            if not <?>: goto 372
        return {'original_sentence': original, 'normalized_sentence': normalized, 'selected_candidate': '', 'best_rule_candidate': '', 'used_rerank': False, 'prototype_enabled': False, 'prototype_hits': [], 'candidates': [], 'salience': salience, 'skipped': True, 'skip_reason': 'sentence_filter'}
        if not Config: goto 388
        getattr(Config, 'MAX_SENTENCE_LENGTH', 512)
        # goto 390
        target_length = 512
        if not Config: goto 414
        getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30)
        # goto 416
        getattr(self, 'max_first_level_length', 30)
        max_len = <?>
        isinstance(max_len, int)
        if not <?>: goto 442
        if not (max_len > 0): goto 442
        # goto 444
        length_budget = None
        if not Config: goto 466
        getattr(Config, 'FIRST_LEVEL_RECALL_ENHANCED', False)
        max_len(bool)
        # goto 468
        recall_enhanced = False
        if not Config: goto 490
        getattr(Config, 'FIRST_LEVEL_BASE_MAX_SPAN', 8)
        <?>(int)
        # goto 492
        base_max_span = 8
        if not Config: goto 516
        getattr(Config, 'FIRST_LEVEL_ENHANCED_MAX_SPAN', 12)
        <?>(int)
        # goto 518
        enhanced_max_span = 12
        focus_markers = ('第一次', '首次', '然而', '最终', '但是', '不过', '却', '更', '更加', '最', '最高', '最低', '核心', '关键', '尤其', '特别', '主要', '重点')
        professional_terms = ('技术', '资源', '平台', '机制', '流程', '生态', '需求', '风险', '压力', '冲突', '协同', '合作', '创新', '服务', '模块', '设备', '系统', '客户', '团队', '品牌', '治理', '监督', '审批', '架构', '算法', '数据', '能力', '知识', '资本', '绩效', '战略', '路径', '场景', '农业', '农村', '种植', '养殖', '灌溉', '施肥', '收割', '农机', '农产品', '粮食', '果蔬', '畜牧', '渔业', '农户', '合作社', '产量', '品种', '有机', '绿色食品', '非遗', '手艺', '技艺', '传承人', '工匠', '作坊', '文创', '手工艺', '陶艺', '织造', '雕刻', '刺绣', '民俗', '古建筑', '修缮', '文保', '文物', '医疗', '诊疗', '康复', '护理', '患者', '医保', '药品', '临床', '公共卫生', '基层医疗', '健康管理', '中医', '慢病', '教育', '教学', '课程', '师资', '学员', '教材', '考核', '素质教育', '职业教育', '技能培训', '校企合作', '在线教育', '社区', '公益', '民生', '基层', '社会组织', '志愿服务', '公共空间', '社区营造', '城市更新', '旧改', '可持续', '赋能', '电商', '直播', '流量', '运营', '供应链', '渠道', '营销', '转化', '复购', '文旅', '景区', '游客', '民宿', '网红', '文旅融合', '打卡')
        # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.strip_punct'()
        strip_punct = ('value', str, 'return', str)
        # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.looks_like_fragment'()
        looks_like_fragment = (professional_terms, self)
        # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.score_candidate'()
        score_candidate = (concessive_spans, focus_markers, length_budget, looks_like_fragment, negated_spans, normalized, professional_terms, prototype_keywords, rag_context_terms, salience, self)
        self._detect_concessive_spans(normalized)
        concessive_spans = ('clean_text', str, 'raw_text', str, 'return', float)
        self._detect_negated_spans(normalized)
        negated_spans = ('raw_text', str, 'clean_text', str, 'return', bool)
        # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<listcomp>'()
        re.split('[\\u3002\\uFF01\\uFF1F\\uFF1B;]', normalized)
        <?>(iter(<?>))
        sentence_parts = <?>
        if sentence_parts: goto 674
        sentence_parts = [normalized]
        candidate_rows = []
        seen = {}
            # for loop body, delta=1236
            sentence_part = iter(sentence_parts)
            # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<listcomp>'()
            re.split('[\\uFF0C,\\u3001]', sentence_part)
            <?>(iter(<?>))
            micro_parts = <?>
            if micro_parts: goto 726
            micro_parts = [sentence_part]
            len(micro_parts)
            <?>(range)
            # for loop body, delta=1232
            i = iter(<?>)
            built_raw = ''
            if not recall_enhanced: goto 756
            # goto 758
            span_limit = base_max_span
            len(micro_parts)
            i(min, (i + span_limit))
            <?>(enhanced_max_span, range)
            # for loop body, delta=1228
            j = iter(<?>)
            if built_raw: goto 802
            # goto 818
            built_raw = 'str(built_raw)，str(micro_parts[j])'
            self._post_refine_phrase(built_raw)
            micro_parts[j](strip_punct)
            candidate = <?>
            if not candidate: goto 846
            # goto 848
            variants = []
            self._normalize_candidate_for_first_level(candidate)
            normalized_candidate = [candidate]
            if not normalized_candidate: goto 886
            if not (normalized_candidate not in variants): goto 886
            variants.append(normalized_candidate)
            if not normalized_candidate: goto 904
            normalized_candidate.replace('就很受影响', '受影响')
            # goto 906
            compact_candidate = ''
            if not compact_candidate: goto 926
            compact_candidate.replace('很受影响', '受影响')
            # goto 928
            compact_candidate = ''
            if not compact_candidate: goto 948
            compact_candidate.replace('影响项目推进', '项目推进受影响')
            # goto 950
            compact_candidate = ''
            if not compact_candidate: goto 978
            if not (compact_candidate not in variants): goto 978
            variants.append(compact_candidate)
            self._compress_first_level_candidate_variants(built_raw)
            <?>(set)
            compressed_variants = <?>
            # for loop body, delta=1024
            compressed_candidate = iter(compressed_variants)
            if not (compressed_candidate not in variants): goto 1020
            variants.append(compressed_candidate)
            # goto 996
            if not normalized_candidate: goto 1070
            if not ('项目推进' in normalized_candidate): goto 1070
            if not ('受影响' in normalized_candidate): goto 1070
            if not ('项目推进受影响' not in variants): goto 1070
            variants.append('项目推进受影响')
            # for loop body, delta=1224
            variant = iter(variants)
            if not variant: goto 1098
            len(variant)
            if not (<?> > target_length): goto 1102
            # goto 1074
            score_candidate(variant, built_raw)
            round(float)
            variant(built_raw, 4)
            row = {'text': <?>, 'raw_text': <?>, 'rule_score': <?>, 'rerank_score': None, 'selected': False, 'best_rule': False, 'compressed_variant': (variant in compressed_variants), 'prototype_hits': prototype_hits}
            seen.get(variant)
            existing = <?>
            if not (existing is None): goto 1190
            len(candidate_rows)
            <?>[seen] = variant
            candidate_rows.append(row)
            # goto 1074
            if not (row['rule_score'] > candidate_rows[existing]['rule_score']): goto 1220
            row[candidate_rows] = existing
            # goto 1074
            # goto 784
            # goto 738
            # goto 686
            if not recall_enhanced: goto 1500
            trigger_keywords = ('影响', '导致', '卡在', '拖慢', '延迟', '只能', '需要', '受限', '不足', '短板', '风险', '压力', '冲突', '审批', '协同', '资源', '客户', '诉求', '反馈', '推进')
            # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<listcomp>'()
            re.split('[，,、；;。！？!?]', normalized)
            <?>(iter(<?>))
            extra_parts = <?>
            # for loop body, delta=1500
            part = iter(extra_parts)
            self._post_refine_phrase(part)
            self._normalize_candidate_for_first_level(strip_punct)
            <?>(<?>)
            clean_part = <?>
            if clean_part: goto 1306
            # goto 1272
            len(clean_part)
            if (<?> < 4): goto 1334
            len(clean_part)
            if not (<?> > target_length): goto 1338
            # goto 1272
            # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<genexpr>'()
            (clean_part,)(iter(trigger_keywords))
            <?>(any)
            if <?>: goto 1366
            # goto 1272
            self._contains_colloquial_residue(clean_part)
            if not <?>: goto 1382
            # goto 1272
            score_candidate(clean_part, part)
            round((float + 0.8))
            clean_part(part, 4)
            row = {'text': <?>, 'raw_text': <?>, 'rule_score': <?>, 'rerank_score': None, 'selected': False, 'best_rule': False}
            seen.get(clean_part)
            existing = <?>
            if not (existing is None): goto 1466
            len(candidate_rows)
            <?>[seen] = clean_part
            candidate_rows.append(row)
            # goto 1272
            if not (row['rule_score'] > candidate_rows[existing]['rule_score']): goto 1496
            row[candidate_rows] = existing
            # goto 1272
            if not recall_enhanced: goto 1804
            if not Config: goto 1804
            getattr(Config, 'FIRST_LEVEL_USE_LABEL_RECALL_CANDIDATES', False)
            if not <?>: goto 1804
            if not Config: goto 1548
            getattr(Config, 'FIRST_LEVEL_SEMANTIC_RECALL_TOP_N', 8)
            <?>(int)
            # goto 1550
            semantic_top_n = 8
            if not Config: goto 1574
            getattr(Config, 'FIRST_LEVEL_SEMANTIC_RECALL_MIN_SCORE', 0.35)
            <?>(float)
            # goto 1576
            semantic_min_score = 0.35
            self._semantic_recall_first_level_labels(normalized, model_manager=model_manager, top_n=semantic_top_n, min_score=semantic_min_score)
            # for loop body, delta=1804
            hit = iter(<?>)
            hit.get('text', '')
            <?>(self._normalize_candidate_for_first_level)
            label = <?>
            if not label: goto 1638
            len(label)
            if not (<?> > target_length): goto 1642
            # goto 1596
            self._contains_colloquial_residue(label)
            if not <?>: goto 1658
            # goto 1596
            hit.get('score', 0.0)
            round((float + (3.0 * 4.0)))
            label(normalized, 4)
            hit.get('score', 0.0)
            round(float)
            False(False, 4)
            row = {'text': <?>, 'raw_text': <?>, 'rule_score': <?>, 'rerank_score': <?>, 'selected': <?>, 'best_rule': <?>, 'semantic_recall_score': None, 'prototype_hits': prototype_hits}
            seen.get(label)
            existing = <?>
            if not (existing is None): goto 1770
            len(candidate_rows)
            <?>[seen] = label
            candidate_rows.append(row)
            # goto 1596
            if not (row['rule_score'] > candidate_rows[existing]['rule_score']): goto 1800
            row[candidate_rows] = existing
            # goto 1596
            hasattr(self, 'knn_abstract_generator')
            if not <?>: goto 2088
            if not (self.knn_abstract_generator is not None): goto 2088

            # try:
            self.knn_abstract_generator.retrieve(normalized, top_k=5, min_score=0.55)
            knn_candidates = <?>
            # for loop body, delta=2064
            knn = iter(knn_candidates)
            knn.get('text', '')
            <?>(self._normalize_candidate_for_first_level)
            label = <?>
            if not label: goto 1894
            len(label)
            if not (<?> > target_length): goto 1898
            # goto 1852
            self._contains_colloquial_residue(label)
            if not <?>: goto 1914
            # goto 1852
            knn.get('score', 0.0)
            <?>(float)
            knn_score = <?>
            round((5.5 + (knn_score * 5.0)), 4)
            round(knn_score, 4)
            knn.get('source_text', '')
            row = {'text': <?>, 'raw_text': <?>, 'rule_score': <?>, 'rerank_score': label, 'selected': normalized, 'best_rule': None, 'knn_source': False, 'knn_score': False, 'knn_source_text': 'v11_abstract', 'prototype_hits': prototype_hits}
            seen.get(label)
            existing = <?>
            if not (existing is None): goto 2030
            len(candidate_rows)
            <?>[seen] = label
            candidate_rows.append(row)
            # goto 1852
            if not (row['rule_score'] > candidate_rows[existing]['rule_score']): goto 2060
            row[candidate_rows] = existing
            # goto 1852
            # goto 2088
            # except matching at 2086
            Exception
            Exception

            # except:
            # goto 2088

            raise
            self._ensure_anchor_index()
            if not <?>: goto 2372
            if not (self.concept_anchor_index is not None): goto 2372

            # try:
            self.concept_anchor_index.search(normalized, top_k,=8)
            anchor_results = <?>
            # for loop body, delta=2348
            <var0>, <var1>, <var2> = iter(anchor_results)
            concept_name = <?>
            anchor_score = <?>
            anchor_source = <?>
            if not (anchor_score < 0.3): goto 2156
            # goto 2132
            self._normalize_candidate_for_first_level(concept_name)
            label = <?>
            if not label: goto 2186
            len(label)
            if not (<?> < 2): goto 2190
            # goto 2132
            round((6.5 + (anchor_score * 4.5)), 4)
            anchor_rule = <?>
            min(anchor_rule, 12.0)
            <?>(((round * 0.5) + (anchor_score * 2.0)), 4)
            anchor_cons = <?>
            round(anchor_score, 4)
            row = {'text': <?>, 'raw_text': label, 'rule_score': normalized, 'rerank_score': anchor_rule, 'conservative_score': None, 'selected': anchor_cons, 'best_rule': False, 'anchor_source': False, 'anchor_score': anchor_source, 'prototype_hits': prototype_hits}
            seen.get(label)
            existing = <?>
            if not (existing is None): goto 2314
            len(candidate_rows)
            <?>[seen] = label
            candidate_rows.append(row)
            # goto 2132
            if not (row['rule_score'] > candidate_rows[existing]['rule_score']): goto 2344
            row[candidate_rows] = existing
            # goto 2132
            # goto 2372
            # except matching at 2370
            Exception
            Exception

            # except:
            # goto 2372

            raise
            _best_non_t5_score = 0.0
            # for loop body, delta=2422
            _r = iter(candidate_rows)
            _r.get('knn_source')
            if not (<?> != 't5_generated'): goto 2418
            _r.get('rule_score', 0.0)
            <?>(max, _best_non_t5_score)
            _best_non_t5_score = <?>
            # goto 2380
            hasattr(self, 't5_generative_coder')
            if not <?>: goto 2762
            if not (self.t5_generative_coder is not None): goto 2762

            # try:
            self.t5_generative_coder.generate(normalized, num_beams=5, num_return=5)
            t5_candidates = <?>
            # for loop body, delta=2738
            tc = iter(t5_candidates)
            tc.get('text', '')
            <?>(self._normalize_candidate_for_first_level)
            label = <?>
            if not label: goto 2512
            len(label)
            if not (<?> > target_length): goto 2516
            # goto 2470
            self._contains_colloquial_residue(label)
            if not <?>: goto 2532
            # goto 2470
            tc.get('score', 0.0)
            <?>(float)
            t5_score = <?>
            if not (_best_non_t5_score < 7.0): goto 2588
            max((4.5 + (t5_score * 0.5)), (_best_non_t5_score - 0.3))
            <?>(round, 4)
            t5_rule = <?>
            # goto 2606
            round((4.0 + (t5_score * 0.5)), 4)
            t5_rule = <?>
            min(t5_rule, 12.0)
            <?>((round * 0.5), 4)
            t5_cons = <?>
            round(t5_score, 4)
            row = {'text': <?>, 'raw_text': label, 'rule_score': normalized, 'rerank_score': t5_rule, 'conservative_score': None, 'selected': t5_cons, 'best_rule': False, 'knn_source': False, 't5_beam_score': 't5_generated', 'prototype_hits': prototype_hits}
            seen.get(label)
            existing = <?>
            if not (existing is None): goto 2704
            len(candidate_rows)
            <?>[seen] = label
            candidate_rows.append(row)
            # goto 2470
            if not (row['rule_score'] > candidate_rows[existing]['rule_score']): goto 2734
            row[candidate_rows] = existing
            # goto 2470
            # goto 2762
            # except matching at 2760
            Exception
            Exception

            # except:
            # goto 2762

            raise
            self._canonicalize_first_level_candidate_rows(candidate_rows, normalized)
            candidate_rows = <?>
            if candidate_rows: goto 2822
            re.search('(生产习惯|默认的惯例|当地默认).*随意', normalized)
            if not <?>: goto 2822
            candidate_rows.append({'text': '规范缺乏', 'raw_text': normalized, 'rule_score': 8.0, 'rerank_score': None, 'selected': False, 'best_rule': False, 'compressed_variant': True, 'conservative_score': 8.0})
            best_rule_candidate = ''
            float('-inf')
            float('-inf')
            float('-inf')
            float('-inf')
            best_rule_key = (<?>, <?>, <?>, <?>)
            # for loop body, delta=2982
            row = iter(candidate_rows)
            row.get('text', '')
            if str: goto 2880 (or pop)
            str('')
            text = <?>
            float('-inf')
            float(row.get, 'conservative_score')
            <?>(<?>)
            re.search('(受影响|受限|受阻|不足|短板|风险|压力|冲突)', text)
            if not <?>: goto 2920
            # goto 2922
            float('-inf')
            float(row.get, 'rule_score')
            1.0(0.0)
            len(text)
            row_key = (<?>, <?>, <?>, -(<?>))
            if not (row_key > best_rule_key): goto 2978
            best_rule_key = row_key
            row.get('text', '')
            best_rule_candidate = <?>
            # goto 2858
            if not best_rule_candidate: goto 2994
            fallback_candidate = best_rule_candidate
            # goto 3068
            if not candidate_rows: goto 3018
            candidate_rows[0].get('text', '')
            fallback_candidate = <?>
            # goto 3068
            strip_punct(normalized)
            <?>(self._normalize_candidate_for_first_level)
            trimmed = <?>
            len(trimmed)
            if not (<?> <= 30): goto 3064
            self._has_first_level_information_cue(trimmed)
            if not <?>: goto 3064
            fallback_candidate = trimmed
            # goto 3068
            fallback_candidate = ''
            selected_candidate = fallback_candidate
            _selected_is_knn = False
            used_rerank = False
            float('-inf')
            if not (<?> > best_rule_key[2]): goto 3106
            # goto 3112
            float('-inf')
            best_rule_score = best_rule_key[2]
            if not selected_candidate: goto 3146
            if not (best_rule_score < 1.5): goto 3146
            if concessive_spans: goto 3142
            if not negated_spans: goto 3146
            selected_candidate = ''
            # try:
            if defer_rerank: goto 3742
            if not Config: goto 3742
            getattr(Config, 'ENABLE_ABSTRACT_RERANKER', False)
            if not <?>: goto 3742
            if not (model_manager is not None): goto 3742
            hasattr(model_manager, 'ensure_abstract_reranker_loaded')
            if not <?>: goto 3206
            model_manager.ensure_abstract_reranker_loaded()
            hasattr(model_manager, 'is_abstract_reranker_available')
            if not <?>: goto 3742
            model_manager.is_abstract_reranker_available()
            if not <?>: goto 3742
            if not Config: goto 3256
            getattr(Config, 'ABSTRACT_RERANK_TOP_N', 6)
            1(int)
            <?>(<?>, max)
            # goto 3258
            rerank_limit = 6
            prefiltered_rows = []
            # for loop body, delta=3416
            row = iter(candidate_rows)
            row.get('text', '')
            if str: goto 3290 (or pop)
            str('')
            t = <?>
            if t: goto 3304
            # goto 3268
            row.get('anchor_source')
            <?>(bool)
            is_anchor = <?>
            if is_anchor: goto 3348
            row.get('raw_text', '')
            <?>(looks_like_fragment, t)
            if not <?>: goto 3348
            # goto 3268
            self._contains_colloquial_residue(t)
            if not <?>: goto 3364
            # goto 3268
            if is_anchor: goto 3402
            row.get('knn_source')
            normalized(bool)
            <?>(<?>, self._is_low_quality_first_level_code, is_knn,=t)
            if not <?>: goto 3402
            # goto 3268
            prefiltered_rows.append(row)
            # goto 3268
            len(prefiltered_rows)
            if not (<?> >= 3): goto 3434
            # goto 3450
            # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<listcomp>'()
            (looks_like_fragment,)(iter(candidate_rows))
            rerank_rows = prefiltered_rows
            if rerank_rows: goto 3466
            list(candidate_rows)
            rerank_rows = <?>
            source_semantic_cues = '(优点|好处|优势|缺点|缺陷|问题|关键|核心|重要|主要|根本|本质|特色|亮点|突破|创新)'
            re.search(source_semantic_cues, normalized)
            <?>(bool)
            source_has_cues = <?>
            # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<lambda>'()
            rerank_rows.sort(key=(source_has_cues, source_semantic_cues), reverse=True)
            # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<listcomp>'()
            <?>(iter(rerank_rows[slice(None, rerank_limit)]))
            rerank_candidates = <?>
            if not rerank_candidates: goto 3742
            model_manager.score_abstract_candidates(normalized, rerank_candidates)
            scores = <?>
            if not scores: goto 3742
            len(scores)
            len(rerank_candidates)
            if not (<?> == <?>): goto 3742
            used_rerank = True
            # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<dictcomp>'()
            zip(rerank_candidates, scores)
            <?>(iter(<?>))
            score_map = <?>
            # for loop body, delta=3660
            row = iter(candidate_rows)
            score_map.get(row['text'])
            <?>[row] = 'rerank_score'
            normalized[row] = 'source_text'
            self._conservative_first_level_rank_score(row)
            round(float)
            <?>(<?>, 4)
            <?>[row] = 'conservative_score'
            # goto 3602
            # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<listcomp>'()
            max(iter(candidate_rows))
            # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<lambda>'()
            <?>(<?>, key=<?>, default=None)
            best_reranked = <?>
            if not (best_reranked is not None): goto 3738
            best_reranked.get('text', selected_candidate)
            selected_candidate = <?>
            best_reranked.get('knn_source')
            if bool: goto 3732 (or pop)
            best_reranked.get('anchor_source')
            <?>(bool)
            _selected_is_knn = <?>
            # goto 3742
            _selected_is_knn = False
            # goto 3766
            # except matching at 3764
            Exception
            Exception

            # except:
            # goto 3766

            raise
            if not selected_candidate: goto 3806
            self._is_semantically_complete(selected_candidate)
            if <?>: goto 3806
            self._limit_first_level_text(selected_candidate, 60)
            candidate = <?>
            if not candidate: goto 3806
            selected_candidate = candidate
            if not (length_budget is not None): goto 3858
            if not selected_candidate: goto 3858
            len(selected_candidate)
            if not (<?> > length_budget): goto 3858
            self._limit_first_level_text(selected_candidate, length_budget)
            candidate = <?>
            if not candidate: goto 3858
            selected_candidate = candidate
            if not selected_candidate: goto 3938
            self._contains_colloquial_residue(selected_candidate)
            if not <?>: goto 3938
            # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<listcomp>'()
            (looks_like_fragment, normalized, self)(iter(candidate_rows))
            clean_rows = <?>
            if not clean_rows: goto 3938
            # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<lambda>'()
            <?>(key=clean_rows.sort, reverse=True)
            clean_rows[0].get('text', selected_candidate)
            selected_candidate = <?>
            # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<genexpr>'()
            (selected_candidate,)(iter(candidate_rows))
            <?>(any)
            _selected_is_anchor = <?>
            strip_punct(selected_candidate)
            if _selected_is_knn: goto 3980 (or pop)
            self._finalize_first_level_candidate(normalized, _selected_is_knn, is_knn,=_selected_is_anchor)
            selected_candidate = <?>
            # for loop body, delta=4030
            row = iter(candidate_rows)
            (row['text'] == selected_candidate)[row] = 'selected'
            (row['text'] == best_rule_candidate)[row] = 'best_rule'
            # goto 3990
            # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<lambda>'()
            <?>(key=candidate_rows.sort, reverse=True)
            isinstance(top_n, int)
            if not <?>: goto 4082
            if not (top_n > 0): goto 4082
            candidate_rows = candidate_rows[slice(None, top_n)]
            # def 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<genexpr>'()
            (selected_candidate,)(iter(candidate_rows))
            <?>(next, None)
            _selected_row = <?>
            if not _selected_row: goto 4126
            _selected_row.get('anchor_source')
            <?>(bool)
            # goto 4128
            _anchor_selected = False
            if not _selected_row: goto 4148
            _selected_row.get('anchor_source', '')
            # goto 4150
            _anchor_source = ''
            bool(prototype_hits)
        return {'original_sentence': <?>, 'normalized_sentence': original, 'selected_candidate': normalized, 'best_rule_candidate': selected_candidate, 'used_rerank': best_rule_candidate, 'prototype_enabled': used_rerank, 'prototype_hits': prototype_hits, 'candidates': candidate_rows, 'salience': salience, 'anchor_selected': _anchor_selected, 'anchor_source': _anchor_source}

    def rewrite_first_level_code(self, text):
        if text: goto 8 (or pop)
        text('')
        str.strip()
        cleaned = <?>
        if cleaned: goto 24
        return ''
        re.sub('(?<=[\\u4e00-\\u9fff])\\?(?=[\\u4e00-\\u9fff])', '，', cleaned)
        cleaned = <?>
        re.sub('^\\s*[\\u2460-\\u2473\\u2776-\\u277F\\u24F5-\\u24FE\\u3251-\\u325F①②③④⑤⑥⑦⑧⑨⑩]+[\\u3001\\.\\uFF0E\\)\\uFF09\\s]*', '', cleaned)
        cleaned = <?>
        re.sub('^\\s*(?:\\d+|[一二三四五六七八九十]+)[\\u3001\\.\\uFF0E\\)\\uFF09]\\s*', '', cleaned)
        cleaned = <?>
        re.sub('^(\\u6211\\u89c9\\u5f97|\\u6211\\u8ba4\\u4e3a|\\u6211\\u611f\\u89c9|\\u5176\\u5b9e|\\u7136\\u540e|\\u5c31\\u662f\\u8bf4|\\u90a3\\u4e48|\\u8fd9\\u4e2a|\\u90a3\\u4e2a|\\u4f60\\u770b|\\u4f60\\u8bf4|\\u5982\\u679c\\u8bf4)+', '', cleaned)
        cleaned = <?>
        re.sub('(\\u8fd9\\u4e2a\\u4e1c\\u897f|\\u8fd9\\u4e2a\\u4e8b\\u60c5|\\u8fd9\\u4ef6\\u4e8b|\\u8fd9\\u4e2a\\u95ee\\u9898)', '', cleaned)
        cleaned = <?>
        re.sub('(\\u53ef\\u80fd|\\u5927\\u6982|\\u4e5f\\u8bb8|\\u597d\\u50cf|\\u5176\\u5b9e|\\u5b9e\\u9645\\u4e0a|\\u8bf4\\u5b9e\\u8bdd|\\u76f8\\u5f53\\u4e8e|\\u5c31\\u662f|\\u7136\\u540e)', '', cleaned)
        cleaned = <?>
        re.sub('(怎么说呢|就是说|我觉得|相当于|要看|分场合|这个东西|这个事情|这个问题)', '', cleaned)
        cleaned = <?>
        re.sub('每个阶段的重点不同.*参与深度是不同的', '阶段性参与调整', cleaned)
        cleaned = <?>
        re.sub('怎么会有人.*?(?:吃饭|消费|购买)', '客源不确定', cleaned)
        cleaned = <?>
        re.sub('咖啡的种植加工活动遵循生产者本人的生产意愿和生产习惯以及当地默认的惯例开展.*随意', '规范缺乏', cleaned)
        cleaned = <?>
        re.sub('生产意愿和生产习惯以及当地默认的惯例开展.*随意', '规范缺乏', cleaned)
        cleaned = <?>
        re.sub('品牌化这个方向', '品牌化方向', cleaned)
        cleaned = <?>
        re.sub('(推动)(?:他们|我们|他|她)(在?)', '\\1\\2', cleaned)
        cleaned = <?>
        re.sub('让他能够更好地带领让他能够更好地带领团队实现技术创新', '团队实现技术创新', cleaned)
        cleaned = <?>
        re.sub('^(?:我们|他们|你们|他|她)(?=(?:在|将|会|对|把)?(?:推动|开展|组织|参与|提出|引入|建立|调整|获得|降低|提高|解决|分析|反馈|合作|转变|优化|对接|支持|购买))', '', cleaned)
        cleaned = <?>
        re.sub('[吧呢啊嘛呀哦哈哎诶噢呃]+$', '', cleaned)
        cleaned = <?>
        re.sub('\\u7ed3\\u679c\\u6210\\u529f\\u4e5f\\u5931\\u8d25', '结果可能成功也可能失败', cleaned)
        cleaned = <?>
        re.sub('(\\u80fd\\u591f|\\u80fd)\\u5f71\\u54cd\\u7684\\u8303\\u56f4', '影响范围', cleaned)
        cleaned = <?>
        re.sub('\\u5f71\\u54cd\\u7684\\u8303\\u56f4', '影响范围', cleaned)
        cleaned = <?>
        re.sub('\\u8fd8\\u662f\\u6709\\u9650\\u7684?$', '有限', cleaned)
        cleaned = <?>
        re.sub('\\u7684(\\u8303\\u56f4|\\u5f71\\u54cd|\\u4f5c\\u7528)', '\\1', cleaned)
        cleaned = <?>
        re.sub('[（(]?\\d{1,2}:\\d{2}[)）]?', '', cleaned)
        cleaned = <?>
        re.sub('\\s+', '', cleaned)
        cleaned = <?>
        re.sub('^(?:\\u6211\\u4EEC|\\u4ED6\\u4EEC|\\u4F60\\u4EEC|\\u4ED6|\\u5979|\\u6211)(?:\\u4E5F|\\u90FD|\\u5C31|\\u4F1A|\\u8981|\\u80FD|\\u53EF\\u4EE5|\\u9700\\u8981|\\u60F3\\u8981|\\u5E0C\\u671B|\\u6253\\u7B97|\\u8BA1\\u5212|\\u51C6\\u5907)?', '', cleaned)
        cleaned = <?>
        re.sub('(?:\\u662F\\u4E0D\\u662F|\\u80FD\\u4E0D\\u80FD|\\u8981\\u4E0D\\u8981|\\u4F1A\\u4E0D\\u4F1A|\\u6709\\u6CA1\\u6709|\\u884C\\u4E0D\\u884C)[\\u3002\\uFF0C]?$', '', cleaned)
        cleaned = <?>
        re.sub('(?:\\u539F\\u56E0\\u662F|\\u662F\\u56E0\\u4E3A|\\u4E3B\\u8981\\u662F|\\u5176\\u5B9E\\u662F)(.{4,30})$', '\\1', cleaned)
        cleaned = <?>
        re.sub('\\u65B9\\u9762\\u7684(?:\\u4E1C\\u897F|\\u4E8B\\u60C5|\\u6D3B|\\u5185\\u5BB9|\\u5DE5\\u4F5C|\\u95EE\\u9898)$', '', cleaned)
        cleaned = <?>
        re.sub('^(.{2,20})(?:\\u7684\\u65B9\\u9762|\\u7684\\u89D2\\u5EA6|\\u7684\\u5C42\\u9762|\\u7684\\u60C5\\u51B5|\\u7684\\u73AF\\u8282|\\u7684\\u9636\\u6BB5|\\u7684\\u8FC7\\u7A0B|\\u7684\\u6D41\\u7A0B|\\u7684\\u6548\\u679C|\\u7684\\u7ED3\\u679C|\\u7684\\u95EE\\u9898)$', '\\1', cleaned)
        cleaned = <?>
        re.sub('^(?:\\u5728|\\u4ECE|\\u7531|\\u5BF9|\\u628A|\\u88AB|\\u8BA9|\\u53EB|\\u7ED9)(.{3,25})$', '\\1', cleaned)
        cleaned = <?>
        re.sub('^(.{4,30})(?:\\u7B49\\u7B49|\\u4E4B\\u7C7B\\u7684|\\u4EC0\\u4E48\\u7684|\\u8FD9\\u4E9B|\\u90A3\\u4E9B)$', '\\1', cleaned)
        cleaned = <?>
        cleaned.strip('，。？！；:"\'()（）[]【】{} ')
        return

    def _rerank_candidate_rows_for_trace(self, trace, score_map):
        trace.get('candidates', [])
        candidates = <?>
        trace.get('normalized_sentence', '')
        normalized = <?>
        trace.get('selected_candidate', '')
        best_text = <?>
        best_score = None
        float('-inf')
        best_rank_score = <?>
            # for loop body, delta=190
            row = iter(candidates)
            row.get('text', '')
            key = (<?>, normalized)
            if not (key not in score_map): goto 90
            None[row] = 'rerank_score'

            # goto 52
            normalized[row] = 'source_text'
            float(score_map[key])
            <?>(round, 4)
            <?>[row] = 'rerank_score'
            self._conservative_first_level_rank_score(row)
            rank_score = <?>
            float(rank_score)
            <?>(round, 4)
            <?>[row] = 'conservative_score'
            if (best_score is None): goto 164
            if not (rank_score > best_rank_score): goto 188
            best_score = row['rerank_score']
            best_rank_score = rank_score
            row.get('text', '')
            best_text = <?>
            # goto 52
            if not (best_score is not None): goto 222
            True[trace] = 'used_rerank'
            self._finalize_first_level_candidate(best_text, normalized)
            <?>[trace] = 'selected_candidate'
            # for loop body, delta=270
            row = iter(candidates)
            row.get('text')
            if (<?> == best_text): goto 262 (or pop)
            row.get('text')
            trace.get('selected_candidate')
            (<?> == (<?> == best_text))[row] = 'selected'
            # goto 226
            # def 'EnhancedCodingGenerator._rerank_candidate_rows_for_trace.<locals>.<lambda>'()
            <?>(key=candidates.sort, reverse=True)
        return None

    def _apply_global_batch_rerank(self, traces, model_manager):
        if not Config: goto 24
        getattr(Config, 'ENABLE_ABSTRACT_RERANKER', False)
        if not <?>: goto 24
        if (model_manager is not None): goto 28
        return None

            # try:
            hasattr(model_manager, 'ensure_abstract_reranker_loaded')
            if not <?>: goto 48
            model_manager.ensure_abstract_reranker_loaded()
            hasattr(model_manager, 'is_abstract_reranker_available')

            if not <?>: goto 66
            model_manager.is_abstract_reranker_available()
            if <?>: goto 72
        return None
        if not Config: goto 112
        getattr(Config, 'ABSTRACT_RERANK_TOP_N', 6)
        getattr(Config, 'FIRST_LEVEL_GLOBAL_RERANK_TOP_N', 24)
        1(int, max)
        <?>(max)
        <?>(<?>, <?>)
        # goto 114
        rerank_limit = 24
        pairs = []
        set()
        seen = <?>
            # for loop body, delta=254
            trace = iter(traces)
            trace.get('normalized_sentence', '')
            normalized = <?>
            # def 'EnhancedCodingGenerator._apply_global_batch_rerank.<locals>.<listcomp>'()
            trace.get('candidates', [])
            <?>(iter((self,)))
            rows = <?>
            # def 'EnhancedCodingGenerator._apply_global_batch_rerank.<locals>.<lambda>'()
            <?>(key=rows.sort, reverse=True)
            # for loop body, delta=252
            row = iter(rows[slice(None, rerank_limit)])
            row.get('text', '')
            pair = (<?>, normalized)
            if not (pair not in seen): goto 250
            seen.add(pair)
            pairs.append(pair)
            # goto 202

            # goto 130
            if pairs: goto 264
        return None
        # def 'EnhancedCodingGenerator._apply_global_batch_rerank.<locals>.<listcomp>'()
        <?>(iter(pairs))
        originals = <?>
        # def 'EnhancedCodingGenerator._apply_global_batch_rerank.<locals>.<listcomp>'()
        <?>(iter(pairs))
        candidates = <?>
        hasattr(model_manager, 'score_abstract_candidate_pairs')
        if not <?>: goto 314
        model_manager.score_abstract_candidate_pairs(pairs)
        scores = <?>
        # goto 326
        model_manager.score_abstract_candidates(originals, candidates)
        scores = <?>
        if not scores: goto 346
        len(scores)
        len(pairs)
        if not (<?> != <?>): goto 352
        return None
        # def 'EnhancedCodingGenerator._apply_global_batch_rerank.<locals>.<dictcomp>'()
        zip(pairs, scores)
        <?>(iter(<?>))
        score_map = <?>
            # for loop body, delta=394
            trace = iter(traces)
            self._rerank_candidate_rows_for_trace(trace, score_map)
            # goto 376
        return None
            # except matching at 452
            Exception
            exc = Exception
            # try:
            logger.warning('全局批量一阶重排失败，回退规则候选: str(exc)')
            # except:
            exc = None
            del exc
        return None
        exc = None
        del exc
        raise 

        raise

    def abstract_sentence(self, sentence, model_manager):
        self._ensure_first_level_defaults()
        if sentence: goto 14 (or pop)
        ''.strip()
        s0 = sentence
        if s0: goto 28
        return ''
        if not (s0 in self.abstract_cache): goto 48
        return self.abstract_cache[s0]
        self.build_first_level_candidate_trace(s0, model_manager,=model_manager)
        trace = <?>
        trace.get('selected_candidate', '')
        compact = <?>
        compact[self.abstract_cache] = s0
        return compact

    def _normalize_source_sentence(self, text):
        if text: goto 8 (or pop)
        text('')
        str.strip()
        normalized = <?>
        if normalized: goto 24
        return ''
        re.sub('^[\\uFF0C\\u3002\\uFF1F\\uFF01\\uFF1B:\\u3001\\.\\?!;\\s]+', '', normalized)
        normalized = <?>
        re.sub('[\\?\\uFF1F]+$', '。', normalized)
        normalized = <?>
        re.sub('[!\\uFF01]+$', '。', normalized)
        normalized = <?>
        re.sub('\\s+', ' ', normalized)
        normalized = <?>
        normalized.strip()
        return

    def _post_refine_phrase(self, text):
        if text: goto 8 (or pop)
        text('')
        refined = str
        getattr(self, 'bad_phrase_patterns', [])
            # for loop body, delta=44
            pattern = iter(<?>)
            re.sub(pattern, '', refined)
            refined = <?>
            # goto 24
            re.sub('[（(]?\\d{1,2}:\\d{2}[)）]?', '', refined)
            refined = <?>
            re.sub('^(\\u56e0\\u6b64|\\u6240\\u4ee5|\\u7136\\u540e|\\u5e76\\u4e14|\\u800c\\u4e14|\\u90a3\\u4e48|\\u5176\\u5b9e)+', '', refined)
            refined = <?>
            re.sub('(\\u56e0\\u6b64|\\u6240\\u4ee5|\\u7136\\u540e|\\u5e76\\u4e14|\\u800c\\u4e14)+$', '', refined)
            refined = <?>
            re.sub('^(\\u8fd9\\u4e2a|\\u90a3\\u4e2a|\\u5b83)(?=[\\u4e00-\\u9fa5])', '', refined)
            refined = <?>
            re.sub('\\s+', '', refined)
            refined = <?>
            refined.replace('“', '')
            <?>.replace('”', '')
            <?>.replace('‘', '')
            <?>.replace('’', '')
            refined = <?>
            refined.strip('，。？！；:"\'()（）[]【】{}“”‘’ ')
        return

    def _is_question_like(self, text):
        if text: goto 8 (or pop)
        text('')
        str.strip()
        t = <?>
        if t: goto 24
        return False
        re.search('[\\?\\uFF1F\\u5417\\u4e48\\u5462]$', t)
        if bool: goto 60 (or pop)
        re.search('(\\u662f\\u4e0d\\u662f|\\u662f\\u5426|\\u80fd\\u4e0d\\u80fd|\\u53ef\\u4e0d\\u53ef\\u4ee5|\\u4f1a\\u4e0d\\u4f1a|\\u6709\\u6ca1\\u6709|\\u8981\\u4e0d\\u8981)', t)

        if bool: goto 60 (or pop)
        re.search('^(\\u4e3a\\u4ec0\\u4e48|\\u600e\\u4e48|\\u5982\\u4f55|\\u54ea[\\u91cc\\u513f\\u4e2a\\u79cd])', t)

        <?>(bool)
        return

    def _compute_salience(self, text):
        if text: goto 8 (or pop)
        text('')
        str.strip()
        t = <?>
        if t: goto 36
        return {'contrast': 0.0, 'causal': 0.0, 'intensity': 0.0, 'problem': 0.0, 'total': 0.0}
        contrast_markers = ('但是', '不过', '然而', '却', '反而', '反倒', '尽管', '虽然', '即使', '即便', '本来.*但', '原以为.*但', '以前.*现在', '过去.*现在', '之前.*后来', '一开始.*后来')
        # def 'EnhancedCodingGenerator._compute_salience.<locals>.<genexpr>'()
        (t,)(iter(contrast_markers))
        [](sum)
        contrast_score = <?>
        min(contrast_score, 3.0)
        contrast_score = <?>
        causal_markers = ('因为', '所以', '因此', '由于', '导致', '致使', '从而', '造成', '引起', '影响', '推动', '促进', '使得', '之所以', '归根结底', '根本原因')
        # def 'EnhancedCodingGenerator._compute_salience.<locals>.<genexpr>'()
        (t,)(iter(causal_markers))
        [](sum)
        causal_score = <?>
        min(causal_score, 3.0)
        causal_score = <?>
        intensity_markers = ('特别', '非常', '最', '极其', '极度', '十分', '根本', '完全', '彻底', '绝对', '毫不', '一直[都在]?', '每次', '总是', '反复', '不断', '太\\w{1,3}$', '很\\w{1,3}$')
        # def 'EnhancedCodingGenerator._compute_salience.<locals>.<genexpr>'()
        (t,)(iter(intensity_markers))
        [](sum)
        intensity_score = <?>
        re.search('[！!]$', t)
        if not <?>: goto 166
        intensity_score += 1.0
        intensity_score = <?>
        min(intensity_score, 3.0)
        intensity_score = <?>
        problem_markers = ('困难', '问题', '矛盾', '冲突', '瓶颈', '障碍', '卡在', '拖慢', '延迟', '受限', '不足', '短板', '风险', '压力', '挑战', '负担', '缺乏', '缺少', '不行', '没办法', '做不了', '无法')
        # def 'EnhancedCodingGenerator._compute_salience.<locals>.<genexpr>'()
        (t,)(iter(problem_markers))
        [](sum)
        problem_score = <?>
        min(problem_score, 3.0)
        problem_score = <?>

        total = ((((problem_score * 1.5) + (contrast_score * 1.2)) + (causal_score * 1.0)) + (intensity_score * 0.8))
        round(contrast_score, 2)
        round(causal_score, 2)
        round(intensity_score, 2)
        round(problem_score, 2)
        round(total, 2)
        return {'contrast': <?>, 'causal': <?>, 'intensity': <?>, 'problem': <?>, 'total': <?>}

    def posseg(text):
        if text: goto 8
        return []
        terms = []
        domain_patterns = ['(?:机制|流程|资源|策略|路径|模式|结构|能力|架构|生态|治理|监督|协同|审批|绩效|战略|需求|服务|创新|评估|优化|配置|整合|调度|保障|约束|反馈|驱动|赋能|转型|传承|保护|非遗|技艺|工艺|文创|文物|修缮|修复|文保|诊疗|康复|护理|医保|健康管理|公共卫生|基层医疗|教学|课程|师资|教材|职业教育|技能培训|素质教育|社区|公益|民生|基层|志愿服务|社区营造|城市更新|旧改|电商|直播|运营|营销|供应链|文旅|景区|民宿|可持续|低碳|绿色|种植|养殖|加工|收购|销售|市场|价格|成本|利润|品牌|质量|标准|有机|合作社|农户|粮食|果蔬|畜牧|渔业|中医|慢病|手工|手艺|织造|雕刻|刺绣|民俗|古建|文物|客户|团队|渠道|产品|数据|平台|系统|设备|算法|培训|考核|认证|检验|补贴|保险|贷款|投资|贸易|消费)']
            # for loop body, delta=80
            pattern = iter(domain_patterns)
            re.findall(pattern, text)
            matches = <?>
            # for loop body, delta=78
            m = iter(matches)
            if not (m not in terms): goto 76
            len(m)
            if not (<?> >= 2): goto 76
            terms.append(m)
            # goto 42

            # goto 22

            # try:
            pseg = posseg
            pseg.cut(text)
            words = <?>
            # for loop body, delta=170
            <var0>, <var1> = iter(words)
            word = <?>
            flag = <?>
            flag.startswith('n')
            if not <?>: goto 168
            len(word)
            if not (<?> >= 2): goto 168
            if not (word not in terms): goto 168
            re.match('^[\\d\\W_]+$', word)
            if <?>: goto 168
            terms.append(word)
            # goto 108
            # goto 192
            # except matching at 190
            Exception
            Exception

            # except:
            # goto 192

            raise
        return terms[slice(None, 20)]

    def _is_coding_worthy_sentence(self, text):
        if text: goto 8 (or pop)
        text('')
        str.strip()
        t = <?>
        if t: goto 24
        return False
        getattr(self, 'coding_worthy_min_length', 10)
        min_len = <?>
        len(t)
        if not (<?> < min_len): goto 52
        return False
        re.match('^(对|嗯|哦|是的|好的|没错|确实|可以|行|好|有|没有|不是)[，,。.!！]?$', t)
        if not <?>: goto 68
        return False
        re.match('^(我|我们)?(觉得|感觉|认为|想|看)(也|都)?(是|就|很|挺|蛮|还|比较)', t)
        if not <?>: goto 94
        self._has_first_level_information_cue(t)
        if <?>: goto 94
        return False
        re.match('^(那我|那我先|我接着说|下一个|接下来|下面|我们先|我先说)', t)
        if not <?>: goto 120
        self._has_first_level_information_cue(t)
        if <?>: goto 120
        return False
        self._compute_salience(t)
        salience = <?>
        getattr(self, 'coding_worthy_min_salience', 1.5)
        min_salience = <?>
        len(t)
        if not (<?> < 20): goto 176
        max(min_salience, 1.8)
        if not (<?> < salience['total']): goto 176
        return False
        if not (salience['total'] < min_salience): goto 232
        self._has_first_level_information_cue(t)
        if <?>: goto 232
        # def 'EnhancedCodingGenerator._is_coding_worthy_sentence.<locals>.<genexpr>'()
        (t,)(iter(('技术', '资源', '平台', '机制', '流程', '生态', '需求', '风险', '压力', '冲突', '协同', '合作', '创新', '服务', '客户', '团队', '品牌', '治理', '监督', '审批', '架构', '数据', '能力', '绩效', '战略', '路径', '场景', '系统', '设备', '模块', '种植', '养殖', '灌溉', '农机', '农产品', '粮食', '合作社', '农户', '非遗', '手艺', '技艺', '传承人', '工匠', '文创', '手工艺', '陶艺', '诊疗', '康复', '护理', '患者', '医保', '药品', '临床', '公共卫生', '教学', '课程', '师资', '学员', '教材', '职业教育', '技能培训', '社区', '公益', '民生', '基层', '志愿服务', '社区营造', '城市更新', '电商', '直播', '运营', '营销', '文旅', '景区', '民宿', '可持续')))
        <?>(sum)
        prof_count = <?>
        if not (prof_count < 2): goto 232
        return False
        return True

    def _should_skip_sentence_for_coding(self, text, salience):
        if text: goto 8 (or pop)
        text('')
        str.strip()
        t = <?>
        if not t: goto 32
        len(t)
        if not (<?> < 10): goto 36
        return True
        re.search('[吗呢呀嘛啊][？?]?$', t)
        if not <?>: goto 52
        return True
        re.search('^(什么|怎么|为什么|如何|哪些|哪方面|什么样|是不是|能不能|要不要|有没有|可不可以|会不会)', t)
        if not <?>: goto 68
        return True
        re.search('^(先给您|先给你|我先|下面我|接下来|首先|本次访谈|这个访谈|刚才|刚刚|旁边|您看|你看|就是说|怎么说)', t)
        if not <?>: goto 84
        return True
        re.match('^(对|嗯|哦|是的|好的|没错|确实|可以|行|好|有|没有|不是)[，,。.!！]?$', t)
        if not <?>: goto 100
        return True
        re.match('^(那我|那我先|我接着说|下一个|接下来|下面|我们先|我先说|你刚刚|你说|你讲)', t)
        if not <?>: goto 116
        return True
        if not salience: goto 162
        salience.get('total', 0)
        if not (<?> < 1.0): goto 162
        self._has_first_level_information_cue(t)
        if <?>: goto 162
        len(t)
        if not (<?> < 30): goto 162
        return True
        re.match('^[\\d\\s\\.\\,\\;\\:\\-\\+\\%\\(\\)（）①②③④⑤⑥⑦⑧⑨⑩]+$', t)
        if not <?>: goto 178
        return True
        return False

    def _formalize_code(self, code):
        if code: goto 8 (or pop)
        code('')
        str.strip()
        ct = <?>
        if ct: goto 24
        return ct
        getattr(self, 'colloquial_to_formal', {})
        mapping = <?>
        mapping.keys()
        <?>(sorted, key=len, reverse=True)
            # for loop body, delta=84
            colloquial = iter(<?>)
            if not (colloquial in ct): goto 82
            ct.replace(colloquial, mapping[colloquial])
            ct = <?>
            # goto 54
            re.sub('(什么的|之类的|那种感觉|这种感觉|这样子|那样子|怎么说呢|就是说)$', '', ct)
            ct = <?>
            re.sub('[吧呢啊嘛呀哦哈哎诶噢呃]+$', '', ct)
            ct = <?>
            re.sub('的(\\w{2,4})$', '\\1', ct)
            ct = <?>
            re.sub('把(.{2,12})(?:聚集|聚拢|吸引)(?:过来|过去|来)', '吸引\\1', ct)
            ct = <?>
            re.sub('^[我我们你你们他他们它它们大家]*(?:也|还是|都|就|会|要|能)?', '', ct)
            ct = <?>
            ct.strip()
            ct = <?>
            if not ct: goto 170
        return ct
        if code: goto 178 (or pop)
        code('')
        str.strip()
        return

    def _compress_first_level_candidate_variants(self, text):
        if text: goto 12 (or pop)
        text('')
        self._normalize_candidate_for_first_level(str)
        base = <?>
        if base: goto 26
        return []
        variants = []
        set()
        seen = <?>
        # def 'EnhancedCodingGenerator._compress_first_level_candidate_variants.<locals>.add'()
        add = (seen, self, variants)
        self._split_first_level_candidate_segments(base)
            # for loop body, delta=216
            part = iter(('value', str))
            add(part)
            re.sub('^(?:我们|他们|你们|大家|客户|企业|项目|平台|它们|这个|那个|这种|那些|这些)?(?:可以|能够|能|会|要|需要|希望|想要|通过|把|将|对|打造|构建|建立|开展|推进|推动)?', '', part)
            compact = <?>
            add(compact)
            re.sub('^.*?(技术|品牌|资源|平台|机制|流程|生态|需求|问题|合作|协同|创新|服务|应用|模块|设备|系统|客户|团队|工业互联网)', '\\1', part)
            compact_tail = <?>
            add(compact_tail)
            # for loop body, delta=172
            transform = iter((('^推动(?:他们|我们|企业|双方)?(.{2,18}(?:合作|交流与合作))$', '\\1'), ('^(?:客户的)?信息系统和(?:我们的)?系统对接$', '客户信息系统对接'), ('^我们购买了?(.{2,16}(?:云存储|云计算|服务))$', '\\1购买'), ('^我们将.{0,12}(生产设备|设备).{0,8}搬到(工业互联网)$', '\\1接入\\2'), ('^我们也会指导客户$', '客户指导协同'), ('^让他能够更好地带领.*?(团队实现技术创新)$', '\\1'), ('^我们从(.{2,16})中找寻灵感$', '\\1启发'), ('^钱已经不再是我的目标了$', '创业目标转变'), ('^我们跟(.{2,18})搞了一个(.{2,12})$', '\\2建设'), ('^一开始书记来找我$', '社区动员参与'), ('^往品牌化这个方向走把粉丝对个人的粘性转嫁到对品牌的粘性$', '品牌粘性转化'), ('^我们自建服务器$', '自建服务器'), ('^每个阶段的重点不同.*?我们参与深度是不同的$', '阶段性参与调整'), ('^我们面临的是自身技术进步$', '自身技术进步压力'), ('^.*生产意愿和生产习惯以及当地默认的惯例开展.*随意$', '规范缺乏')))
            re.sub(transform[0], transform[1], part)
            replaced = <?>
            if not (replaced != part): goto 170
            add(replaced)
            # goto 128
            # for loop body, delta=214
            pattern = iter(('((?:影响|导致|推动|推进|解决|分析|反馈|合作|转变|优化|对接|支持|审批|协调|整合|开发|探索|识别|建立|引入|获得|提高|降低|调整|打造|构建|涵养|塑造|形成|提升|购买|指导)[^，,、；;。！？!?]{2,14})', '([^，,、；;。！？!?]{2,10}(?:受影响|受限|受阻|不足|短板|风险|压力|冲突))', '((?:客户|市场|项目|资源|技术|流程|机制|服务|需求|机会|风险|问题|品牌|生态|平台|应用|模块|设备|合作|系统|团队|工业互联网)[^，,、；;。！？!?]{1,10}(?:需求|诉求|反馈|协同|整合|优化|推进|支持|识别|解决|不足|风险|合作|赋能|创新|共创|共享|建立|提升|应用|对接|接入|购买|指导))'))
            re.finditer(pattern, part)
            # for loop body, delta=212
            match = iter(<?>)
            match.group(1)
            <?>(add)
            # goto 192

            # goto 176

            # goto 68
        return variants

    def _normalize_candidate_for_first_level(self, text):
        if text: goto 8 (or pop)
        text('')
        str.strip()
        refined = <?>
        if refined: goto 24
        return ''
        re.sub('(?<=[\\u4e00-\\u9fff])\\?(?=[\\u4e00-\\u9fff])', '，', refined)
        refined = <?>
        re.sub('^\\s*[\\u2460-\\u2473\\u2776-\\u277F\\u24F5-\\u24FE\\u3251-\\u325F①②③④⑤⑥⑦⑧⑨⑩]+[\\u3001\\.\\uFF0E\\)\\uFF09\\s]*', '', refined)
        refined = <?>
        re.sub('^\\s*(?:\\d+|[一二三四五六七八九十]+)[\\u3001\\.\\uFF0E\\)\\uFF09]\\s*', '', refined)
        refined = <?>
        re.sub('^(\\u4f60\\u8bf4|\\u4f60\\u770b|\\u5982\\u679c|\\u8981\\u662f|\\u5047\\u5982|\\u5176\\u5b9e|\\u4f46\\u662f|\\u4e0d\\u8fc7|\\u6240\\u4ee5|\\u56e0\\u6b64|\\u7136\\u540e|\\u5e76\\u4e14|\\u800c\\u4e14|\\u90a3\\u4e48|\\u56e0\\u4e3a)+', '', refined)
        refined = <?>
        re.sub('^(\\u6211\\u4eec\\u901a\\u8fc7|\\u6211\\u4eec\\u5c31\\u53ef\\u4ee5|\\u6211\\u4eec\\u5c31\\u80fd|\\u6211\\u4eec\\u5c31\\u662f|\\u6211\\u4eec\\u628a|\\u6211\\u4eec\\u53bb|\\u6211\\u4eec\\u6765)+', '', refined)
        refined = <?>
        re.sub('^(\\u8fd9\\u4e2a\\u6d41\\u7a0b|\\u8fd9\\u4e2a\\u95ee\\u9898|\\u8fd9\\u4e2a\\u4e8b\\u60c5|\\u8fd9\\u4e2a\\u60c5\\u51b5)', '', refined)
        refined = <?>
        re.sub('(\\u662f\\u4e0d\\u662f|\\u662f\\u5426|\\u80fd\\u4e0d\\u80fd|\\u53ef\\u4e0d\\u53ef\\u4ee5|\\u4f1a\\u4e0d\\u4f1a|\\u6709\\u6ca1\\u6709|\\u8981\\u4e0d\\u8981)', '', refined)
        refined = <?>
        re.sub('^(\\u4e3a\\u4ec0\\u4e48|\\u600e\\u4e48|\\u5982\\u4f55)', '', refined)
        refined = <?>
        re.sub('[（(]?\\d{1,2}:\\d{2}[)）]?', '', refined)
        refined = <?>
        re.sub('\\u7684\\u8bdd', '', refined)
        refined = <?>
        re.sub('\\u7684\\u65f6\\u5019', '', refined)
        refined = <?>
        re.sub('(怎么说呢|就是说|我觉得|相当于|要看|分场合|这个东西|这个事情|这个问题)', '', refined)
        refined = <?>
        re.sub('[吧呢啊嘛呀哦哈哎诶噢呃]+$', '', refined)
        refined = <?>
        re.sub('\\u6bcf\\u6b21\\u90fd', '经常', refined)
        refined = <?>
        re.sub('\\u8fd9\\u91cc$', '', refined)
        refined = <?>
        re.sub('(\\u5c31\\u5f88\\u53d7\\u5f71\\u54cd|\\u5f88\\u53d7\\u5f71\\u54cd)', '受影响', refined)
        refined = <?>
        re.sub('\\u6211\\u4eec\\u5c31\\u53ea\\u80fd', '只能', refined)
        refined = <?>
        re.sub('\\u6211\\u4eec\\u53ea\\u80fd', '只能', refined)
        refined = <?>
        refined.replace('自己', '自行')
        refined = <?>
        refined.replace('一直催', '催促')
        refined = <?>
        refined.replace('不够', '不足')
        refined = <?>
        refined.replace('太慢', '过慢')
        refined = <?>
        refined.replace('客户的反馈', '客户反馈')
        refined = <?>
        refined.replace('分析客户的反馈', '分析客户反馈')
        refined = <?>
        refined.replace('别的组的设备', '别组设备')
        refined = <?>
        refined.replace('借别组设备来做', '借用别组设备')
        refined = <?>
        re.sub('\\s+', '', refined)
        refined = <?>
        refined.replace('“', '')
        <?>.replace('”', '')
        <?>.replace('‘', '')
        <?>.replace('’', '')
        refined = <?>
        refined.strip('，。？！；:"\'()（）[]【】{}“”‘’ ')
        return

    def _is_semantically_complete(self, text):
        if text: goto 6 (or pop)
        ''.strip()
        t = text
        if t: goto 20
        return False
        len(t)
        if not (<?> < 4): goto 36
        return False
        self._is_question_like(t)
        if not <?>: goto 50
        return False
        re.search('(\\u600e\\u4e48|\\u5982\\u4f55|\\u8fd9\\u91cc|\\u8fd9\\u6837|\\u90a3\\u6837|\\u8fd9\\u79cd|\\u8fd9\\u4e9b|\\u90a3\\u4e9b|\\u8fd9\\u7c7b|\\u90a3\\u7c7b)$', t)
        if not <?>: goto 66
        return False
        re.search('^(\\u56e0\\u4e3a|\\u5982\\u679c|\\u5373\\u4f7f|\\u867d\\u7136|\\u4f46\\u662f|\\u4e0d\\u8fc7|\\u6240\\u4ee5|\\u56e0\\u6b64|\\u7136\\u540e|\\u5e76\\u4e14|\\u800c\\u4e14)$', t)
        if not <?>: goto 82
        return False
        re.search('^(\\u56e0\\u4e3a|\\u5982\\u679c|\\u5373\\u4f7f|\\u867d\\u7136)', t)
        if not <?>: goto 110
        re.search('(\\u6240\\u4ee5|\\u56e0\\u6b64|\\u5bfc\\u81f4|\\u4f7f\\u5f97|\\u4ece\\u800c|\\u53ea\\u80fd|\\u5f71\\u54cd)', t)
        if <?>: goto 110
        return False
        re.search('^(\\u6211|\\u6211\\u4eec|\\u4f60|\\u4f60\\u4eec).*(\\u4e0d\\u592a\\u6e05\\u695a|\\u4e0d\\u77e5\\u9053|\\u4e0d\\u786e\\u5b9a|\\u8bf4\\u4e0d\\u597d)', t)
        if not <?>: goto 126
        return False
        re.search('^(\\u8fd8\\u53ef\\u4ee5|\\u8fd8\\u597d|\\u5dee\\u4e0d\\u591a|\\u4e00\\u822c\\u822c?)$', t)
        if not <?>: goto 142
        return False
        return True

    def _detect_concessive_spans(self, text):
        concessive_starters = ('\\u5c31\\u7b97(?:\\u662f)?', '\\u5373\\u4fbf(?:\\u662f)?', '\\u5373\\u4f7f(?:\\u662f)?', '\\u54ea\\u6015(?:\\u662f)?', '\\u5c3d\\u7ba1(?:\\u662f)?', '\\u867d\\u7136(?:\\u662f)?', '\\u65e0\\u8bba(?:\\u662f|\\u5982\\u4f55|\\u600e\\u6837)?', '\\u4e0d\\u7ba1(?:\\u662f|\\u5982\\u4f55|\\u600e\\u6837)?', '\\u7eb5\\u4f7f(?:\\u662f)?', '\\u4efb\\u51ed(?:\\u662f)?', '\\u5982\\u679c\\u53ea\\u662f', '\\u5982\\u679c\\u4ec5\\u4ec5', '\\u5982\\u679c\\u5149', '\\u5982\\u679c\\u5149\\u5149', '\\u5047\\u5982\\u53ea\\u662f', '\\u5047\\u5982\\u4ec5\\u4ec5', '\\u8981\\u662f\\u53ea\\u662f', '\\u8981\\u662f\\u4ec5\\u4ec5')

        re.compile('[\\uff0c,\\u3002\\uff01!\\uff1f?\\uff1b;]|\\u4f46(?:\\u662f)?|\\u4e0d\\u8fc7|\\u7136\\u800c|\\u5374|\\u53ef(?:\\u662f)?|\\u5176\\u5b9e|\\u5b9e\\u9645\\u4e0a|\\u7684\\u8bdd')
        clause_end_pattern = []
        spans = []
            # for loop body, delta=128
            starter = iter(concessive_starters)
            re.finditer(starter, text)
            # for loop body, delta=126
            m = iter(<?>)
            m.end()
            content_start = <?>
            rest = text[slice(content_start, None)]
            clause_end_pattern.search(rest)
            end_match = <?>
            if not end_match: goto 94
            end_match.start()
            content_end = (<?> + content_start)
            # goto 102
            len(text)
            content_end = <?>
            if not (content_end > content_start): goto 124
            spans.append((content_start, content_end))
            # goto 42

            # goto 26
        return spans

    def _detect_negated_spans(self, text):
        spans = []

        re.compile('\\u5bf9(.{2,40}?)(?:\\u5e76?\\u4e0d(?:\\u662f|\\u592a|\\u7279\\u522b|\\u600e\\u4e48|\\u662f\\u5f88)?|\\u5e76\\u975e|\\u6ca1(?:\\u6709)?)(?:.{0,20})(?:\\u5728\\u610f|\\u5728\\u4e4e|\\u5173\\u5fc3|\\u91cd\\u89c6|\\u611f\\u5174\\u8da3|\\u770b\\u91cd|\\u8981\\u6c42|\\u5f3a\\u6c42|\\u7ea0\\u7ed3|\\u8ba1\\u8f83|\\u770b\\u5f97\\u591a\\u91cd|\\u5f88\\u5927\\u5173\\u7cfb|\\u7279\\u610f|\\u4ecb\\u610f|\\u6240\\u8c13)')
        pattern1 = <?>
        pattern1.finditer(text)
            # for loop body, delta=56
            m = iter(<?>)
            m.start(1)
            m.end(1)
            <?>((<?>, spans.append))
            # goto 24

            re.compile('(?:\\u4e0d\\u5728\\u4e4e|\\u4e0d\\u5728\\u610f|\\u4e0d\\u5173\\u5fc3|\\u4e0d\\u91cd\\u8981|\\u65e0\\u6240\\u8c13|\\u6ca1\\u5173\\u7cfb|\\u4e0d\\u770b\\u91cd|\\u4e0d\\u600e\\u4e48\\u770b\\u91cd|\\u4e0d\\u662f\\u7279\\u522b\\u5728\\u610f|\\u4e0d\\u592a\\u5728\\u610f|\\u5e76\\u4e0d\\u5728\\u610f)(.{2,25}?)(?:[\\uff0c,\\u3002\\uff01!\\uff1f?\\uff1b;]|\\u4f46|\\u5176\\u5b9e|$)')
            pattern2 = <?>
            pattern2.finditer(text)
            # for loop body, delta=108
            m = iter(<?>)
            m.start(1)
            m.end(1)
            <?>((<?>, spans.append))
            # goto 76

            re.compile('(?:\\u4e0d\\u89c9\\u5f97|\\u4e0d\\u8ba4\\u4e3a|\\u6ca1\\u89c9\\u5f97|\\u4e0d\\u4f1a\\u89c9\\u5f97)(.{2,30}?)(?:[\\uff0c,\\u3002\\uff01!\\uff1f?\\uff1b;]|$)')
            pattern3 = <?>
            pattern3.finditer(text)
            # for loop body, delta=160
            m = iter(<?>)
            m.start(1)
            m.end(1)
            <?>((<?>, spans.append))
            # goto 128
        return spans

    def _truncate_to_word(self, text, max_length):
        if text: goto 6 (or pop)
        ''.strip()
        t = text
        if (max_length <= 0): goto 32
        len(t)
        if not (<?> <= max_length): goto 36
        return t
        t[slice(None, max_length)].rstrip('，。？！；:"\'()（）[]【】{} ')
        cut = <?>
        range(6)
            # for loop body, delta=128
            _ = iter(<?>)
            if cut: goto 74
            # goto 128
            re.search('(\\u600e\\u4e48|\\u5982\\u4f55|\\u8fd9\\u91cc|\\u8fd9\\u6837|\\u90a3\\u6837|\\u8fd9\\u79cd|\\u8fd9\\u4e9b|\\u90a3\\u4e9b|\\u8fd9\\u7c7b|\\u90a3\\u7c7b)$', cut)
            if not <?>: goto 100
            cut = cut[slice(None, -1)]

            # goto 62
            re.search('(\\u56e0\\u4e3a|\\u5982\\u679c|\\u5373\\u4f7f|\\u867d\\u7136|\\u4f46\\u662f|\\u4e0d\\u8fc7|\\u6240\\u4ee5|\\u56e0\\u6b64|\\u7136\\u540e|\\u5e76\\u4e14|\\u800c\\u4e14)$', cut)
            if not <?>: goto 126
            cut = cut[slice(None, -1)]

            # goto 62
            cut.strip('，。？！；:"\'()（）[]【】{} ')
        return

    def _smart_abbreviate(self, text, max_length):
        if text: goto 8 (or pop)
        text('')
        str.strip()
        t = <?>
        if not t: goto 40
        if (max_length <= 0): goto 40
        len(t)
        if not (<?> <= max_length): goto 44
        return t
        # def 'EnhancedCodingGenerator._smart_abbreviate.<locals>.<listcomp>'()
        re.split('[\\uFF0C,\\u3001]', t)
        <?>(iter(<?>))
        parts = <?>
        len(parts)
        if not (<?> <= 1): goto 90
        self._truncate_to_word(t, max_length)
        return

        re.compile('(\\u673A\\u5236|\\u6D41\\u7A0B|\\u8D44\\u6E90|\\u7B56\\u7565|\\u8DEF\\u5F84|\\u6A21\\u5F0F|\\u7ED3\\u6784|\\u80FD\\u529B|\\u67B6\\u6784|\\u751F\\u6001|\\u6CBB\\u7406|\\u76D1\\u7763|\\u534F\\u540C|\\u5BA1\\u6279|\\u7EE9\\u6548|\\u6218\\u7565|\\u9700\\u6C42|\\u670D\\u52A1|\\u521B\\u65B0|\\u8BC4\\u4F30|\\u4F18\\u5316|\\u914D\\u7F6E|\\u6574\\u5408|\\u4FDD\\u969C|\\u7EA6\\u675F|\\u53CD\\u9988|\\u9A71\\u52A8|\\u8D4B\\u80FD|\\u8F6C\\u578B|\\u4E0D\\u8DB3|\\u53D7\\u9650|\\u7F3A\\u5931|\\u7F3A\\u4E4F|\\u53D7\\u963B|\\u5EF6\\u8FDF|\\u5F71\\u54CD|\\u63A8\\u52A8|\\u964D\\u4F4E|\\u589E\\u52A0|\\u5BA2\\u6237|\\u56E2\\u961F|\\u54C1\\u724C|\\u5E73\\u53F0|\\u7CFB\\u7EDF|\\u6570\\u636E|\\u5B89\\u5168|\\u8D28\\u91CF|\\u6210\\u672C|\\u6548\\u7387)')
        high_value_words = <?>
        # def 'EnhancedCodingGenerator._smart_abbreviate.<locals>.part_score'()
        part_score = (high_value_words,)
        sorted(parts, key=part_score, reverse=True)
        ranked = ('part', str, 'return', float)
        selected = []
        current_len = 0
            # for loop body, delta=200
            part = iter(ranked)
            len(part)
            if not selected: goto 170
            # goto 172
            test_len = (1 + 0)
            if not (test_len <= max_length): goto 198
            selected.append(part)
            (<?> + current_len)
            current_len = test_len
            # goto 148
            if not selected: goto 214
            '，'.join(selected)
        return
        best_part = ranked[0]
        self._truncate_to_word(best_part, max_length)
        return

    def _limit_first_level_text(self, text, max_length):
        if text: goto 6 (or pop)
        ''.strip()
        t = text
        if t: goto 20
        return ''
        if not (max_length <= 0): goto 32
        return t
        len(t)
        if not (<?> <= max_length): goto 48
        return t
        # def 'EnhancedCodingGenerator._limit_first_level_text.<locals>.<listcomp>'()
        re.split('[\\uFF0C,\\u3002]', t)
        <?>(iter(<?>))
        parts = <?>
        if parts: goto 86
        self._truncate_to_word(t, max_length)
        return
        best = ''
        len(parts)
        <?>(range)
            # for loop body, delta=224
            i = iter(<?>)
            built = ''
            len(parts)
            <?>(range, i)
            # for loop body, delta=222
            j = iter(<?>)
            if built: goto 140
            # goto 156
            built = 'str(built)，str(parts[j])'
            len(built)
            if not (parts[j] > max_length): goto 174
            # goto 222
            built.strip('，。？！；:"\'()（）[]【】{} ')
            cand = <?>
            if cand: goto 190

            # goto 124
            self._is_semantically_complete(cand)
            if not <?>: goto 220
            len(cand)
            len(best)
            if not (<?> > <?>): goto 220
            best = cand
            # goto 124
            # goto 102
            if not best: goto 232
        return best
        self._smart_abbreviate(t, max_length)
        return

    def generate_codes_with_trained_model(self, processed_data, model_manager, progress_callback, coding_thresholds):
            # try:
            self._apply_similarity_threshold_options(coding_thresholds)
            self._ensure_rag_threshold_defaults()
            if not progress_callback: goto 34
            progress_callback(10)
            model_manager.is_trained_model_available()
            if <?>: goto 50
            ValueError('没有可用的训练模型，请先训练模型')
            raise <?>
            all_sentences = []
            processed_data.get('file_sentence_mapping', {})
            file_sentence_mapping = <?>
            file_sentence_mapping.items()
            # for loop body, delta=106
            <var0>, <var1> = iter(<?>)
            filename = <?>
            file_data = <?>
            file_data.get('sentences', [])
            sentences = <?>
            all_sentences.extend(sentences)
            # goto 74
            if not progress_callback: goto 118
            progress_callback(30)
            filtered_sentences = []
            texts = []
            # for loop body, delta=186
            sent = iter(all_sentences)
            sent.get('content', '')
            if <?>: goto 148 (or pop)
            ''.strip()
            t = <?>
            self._is_coding_worthy_sentence(t)
            if not <?>: goto 184
            filtered_sentences.append(sent)
            texts.append(t)
            # goto 130
            if texts: goto 198
            ValueError('没有找到有效的文本内容')
            raise <?>
            if not progress_callback: goto 210
            progress_callback(50)
            model_manager.predict_categories(texts)
            <var0>, <var1> = <?>
            predictions = <?>
            predicted_labels = <?>
            if not progress_callback: goto 236
            progress_callback(70)
            first_level_codes = {}
            second_level_mapping = {}
            self.reset_first_level_trace_meta()
            third_level_mapping = {}
            use_semantic_matching = False
            second_level_codes_list = []
            third_level_codes_list = []
            if not self.coding_library: goto 380
            if not self.semantic_matcher: goto 380

            # try:
            self.coding_library.get_all_second_level_codes()
            second_level_codes_list = <?>
            self.coding_library.get_all_third_level_codes()
            third_level_codes_list = <?>
            if not second_level_codes_list: goto 324
            if not third_level_codes_list: goto 324
            use_semantic_matching = True
            logger.info('使用语义相似度匹配进行编码')
            # goto 380
            # except matching at 378
            Exception
            e = Exception
            # try:
            logger.error('获取编码库失败: str(e)')
            # except:
            e = None
            del e
            # goto 380
            e = None
            del e
            raise 

            raise
            if coding_thresholds: goto 388 (or pop)
            {}.get('use_global_batch_rerank', False)
            bool(coding_thresholds)
            use_global_batch_rerank = <?>
            global_traces = []
            if not use_global_batch_rerank: goto 442
            # def 'EnhancedCodingGenerator.generate_codes_with_trained_model.<locals>.<listcomp>'()
            (model_manager, self)(iter(texts))
            global_traces = <?>
            self._apply_global_batch_rerank(global_traces, model_manager,=model_manager)
            zip(texts, predicted_labels)
            <?>(enumerate)
            # for loop body, delta=1502
            <var0>, <var1> = iter(<?>)
            i = <?>
            <var0>, <var1> = <?>
            text = <?>
            label = <?>
            code_key = "(i + 1)format('04d')"

            if not use_global_batch_rerank: goto 510
            len(global_traces)
            if not ('FL_' < i): goto 510
            # goto 522
            self.build_first_level_candidate_trace(text, model_manager,=model_manager)

            trace = global_traces[i]
            trace.get('selected_candidate', '')
            abstracted = <?>
            self._repair_first_level_sentence_detail(filtered_sentences[i])
            source_detail = <?>
            source_detail.get('sentence_id')
            if <?>: goto 576
            self._store_first_level_trace(code_key, trace)

            # goto 456
            self._select_quality_first_level_candidate(trace, source_detail)
            abstracted = <?>
            if abstracted: goto 608
            self._store_first_level_trace(code_key, trace)

            # goto 456
            self._clean_code_prefix(abstracted)
            abstracted = <?>
            [abstracted, [source_detail], 1, 1, [source_detail]][first_level_codes] = code_key
            self._store_first_level_trace(code_key, trace)
            if not use_semantic_matching: goto 1208
            if not abstracted: goto 1208
            top_k = 5
            cache_key = 'str(abstracted)_str(top_k)_0.3'
            if not (cache_key in self.similarity_cache): goto 718
            logger.info('使用缓存的相似度计算结果')
            matches = self.similarity_cache[cache_key]
            # goto 750
            self.semantic_matcher.match_first_level_to_second_level(abstracted, second_level_codes_list, top_k=top_k, threshold=self.rag_second_level_threshold)
            matches = <?>
            matches[self.similarity_cache] = cache_key
            if not matches: goto 1176
            if not model_manager: goto 1126
            model_manager.is_trained_model_available()
            if not <?>: goto 1126
            len(matches)
            <?>("logger.infostr('使用bert_finetuned模型对 ') 个候选进行重排")
            # def 'EnhancedCodingGenerator.generate_codes_with_trained_model.<locals>.<listcomp>'()
            <?>(iter(matches))
            candidate_codes = <?>

            # try:
            # def 'EnhancedCodingGenerator.generate_codes_with_trained_model.<locals>.<listcomp>'()
            (abstracted,)(iter(candidate_codes))
            inputs = <?>
            model_manager.predict_categories(inputs)
            <var0>, <var1> = <?>
            predictions = <?>
            _ = <?>
            confidences = []
            # for loop body, delta=898
            pred = iter(predictions)
            isinstance(pred, tuple)
            if not <?>: goto 884
            confidences.append(pred[1])
            # goto 850
            confidences.append(0.0)
            # goto 850
            if not confidences: goto 972
            max(confidences)
            <?>(confidences.index)
            best_idx = <?>
            <var0>, <var1> = matches[best_idx]
            best_match = <?>
            _ = <?>
            best_match.get('name')
            second_cat = <?>
            max(confidences)
            logger.info("bert_finetuned模型选择的二阶编码: str(second_cat) (置信度: format('.4f'))")
            # goto 1020
            <var0>, <var1> = matches[0]
            best_match = <?>
            similarity = <?>
            best_match.get('name')
            second_cat = <?>
            "回退到相似度匹配: '"("str(second_cat) (相似度: similarityformat('.4f'))")
            logger.info
            # goto 1266
            # except matching at 1124
            Exception
            e = Exception
            # try:
            logger.warning('模型重排失败，回退到相似度匹配: str(e)')
            <var0>, <var1> = matches[0]
            best_match = <?>
            similarity = <?>
            best_match.get('name')
            second_cat = <?>
            "回退到相似度匹配: '"("str(second_cat) (相似度: similarityformat('.4f'))")
            logger.info
            # except:
            e = None
            del e
            # goto 1266
            e = None
            del e
            raise 

            raise
            <var0>, <var1> = matches[0]
            best_match = <?>
            similarity = <?>
            best_match.get('name')
            second_cat = <?>
            "未加载训练模型，使用相似度匹配: '"("str(second_cat) (相似度: similarityformat('.4f'))")
            logger.info
            # goto 1266
            second_cat = '其他各类话题'
            logger.info("一阶编码 str(abstracted[slice(None, 30)])...' 未找到匹配的二阶编码，归类为'其他各类话题")
            # goto 1266
            if not ('||' in label): goto 1236
            label.split('||', 1)
            <var0>, <var1> = <?>
            third_cat_pred = <?>
            second_cat = <?>
            # goto 1250
            if not label: goto 1246
            # goto 1248
            second_cat = '其他'
            logger.info('使用训练模型预测的二阶编码: str(second_cat)')
            label
            second_cat[second_level_mapping] = code_key
            if not use_semantic_matching: goto 1444
            second_code = None
            # for loop body, delta=1320
            code = iter(second_level_codes_list)
            code.get('name')
            if not (<?> == second_cat): goto 1316
            second_code = code
            # goto 1320
            # goto 1288
            if not second_code: goto 1428
            self.semantic_matcher.match_second_level_to_third_level(second_code, third_level_codes_list, threshold,=self.rag_third_level_threshold)
            match = <?>
            if not match: goto 1404
            <var0>, <var1> = match
            best_match = <?>
            similarity = <?>
            best_match.get('name')
            third_cat = <?>
            "二阶编码 '"("str(second_cat) 匹配到三阶编码 str(third_cat) (相似度: similarityformat('.4f'))")
            logger.info
            # goto 1492
            third_cat = '其他重要维度'
            logger.info("二阶编码 str(second_cat) 未找到匹配的三阶编码，归类为'其他重要维度")
            # goto 1492
            third_cat = '其他重要维度'
            logger.info("未找到对应的二阶编码，三阶编码归类为'其他重要维度'")
            # goto 1492
            if not ('||' in label): goto 1472
            label.split('||', 1)
            <var0>, <var1> = <?>
            third_cat = <?>
            _ = <?>
            # goto 1476
            third_cat = '综合主题'
            logger.info('使用训练模型预测的三阶编码: str(third_cat)')
            third_cat[third_level_mapping] = second_cat
            # goto 456
            if not progress_callback: goto 1516
            progress_callback(85)
            defaultdict(list)
            second_level_codes = <?>
            second_level_mapping.items()
            # for loop body, delta=1558
            <var0>, <var1> = iter(<?>)
            code_key = <?>
            second_cat = <?>
            second_level_codes[second_cat].append(code_key)
            # goto 1532
            defaultdict(list)
            third_level_codes = <?>
            third_level_mapping.items()
            # for loop body, delta=1600
            <var0>, <var1> = iter(<?>)
            second_cat = <?>
            third_cat = <?>
            third_level_codes[third_cat].append(second_cat)
            # goto 1574
            if not progress_callback: goto 1614
            progress_callback(100)
            if not model_manager: goto 1640
            hasattr(model_manager, 'release_model_resources')
            if not <?>: goto 1640
            model_manager.release_model_resources()
            dict(first_level_codes)
            dict(second_level_codes)
            dict(third_level_codes)
        return {'一阶编码': <?>, '二阶编码': <?>, '三阶编码': <?>, 'file_sentence_mapping': file_sentence_mapping}
            # except matching at 1806
            Exception
            e = Exception
            # try:
            str(e)
            <?>("logger.errorstr('使用训练模型生成编码失败: ')")
            traceback = <?>
            traceback.print_exc()
            if not model_manager: goto 1746
            hasattr(model_manager, 'release_model_resources')
            if not <?>: goto 1746
            model_manager.release_model_resources()
            str(e)
            # except:
            e = None
            del e
        return ['请检查训练模型']
        e = None
        del e
        raise '错误'

        raise
        {'一阶编码': '错误', '二阶编码': ['模型预测失败'], '三阶编码': {}}
        {}
        {}
        ["错误str('使用训练模型生成编码失败: ')"]

    def generate_grounded_theory_codes_multi_files(self, processed_data, model_manager, progress_callback, use_trained_model, coding_thresholds):
        if not use_trained_model: goto 30
        model_manager.is_trained_model_available()
        if not <?>: goto 30
        self.generate_codes_with_trained_model(processed_data, model_manager, progress_callback, coding_thresholds,=coding_thresholds)
        return
        self.generate_codes_with_rules(processed_data, progress_callback, model_manager=model_manager, coding_thresholds=coding_thresholds)
        return

    def generate_codes_with_rules(self, processed_data, progress_callback, model_manager, coding_thresholds):
            # try:
            self._apply_similarity_threshold_options(coding_thresholds)
            self._ensure_rag_threshold_defaults()
            if not progress_callback: goto 32
            progress_callback(10)
            combined_text = processed_data['combined_text']
            file_sentence_mapping = processed_data['file_sentence_mapping']
            all_sentences = []
            file_sentence_mapping.items()
            # for loop body, delta=92
            <var0>, <var1> = iter(<?>)
            filename = <?>
            file_data = <?>
            file_data.get('sentences', [])
            sentences = <?>
            all_sentences.extend(sentences)
            # goto 60
            if not progress_callback: goto 104
            progress_callback(30)
            self.generate_first_level_codes(all_sentences, model_manager=model_manager, coding_options=coding_thresholds)
            first_level_codes = <?>
            len(first_level_codes)
            <?>("logger.infostr('生成 ') 个一阶编码")
            if not progress_callback: goto 154
            progress_callback(60)
            self.generate_second_level_codes_improved(first_level_codes, model_manager,=model_manager)
            second_level_codes = <?>
            len(second_level_codes)
            <?>("logger.infostr('生成 ') 个二阶编码")
            if not progress_callback: goto 202
            progress_callback(80)
            self.generate_third_level_codes_improved(second_level_codes)
            third_level_codes = <?>
            len(third_level_codes)
            <?>("logger.infostr('生成 ') 个三阶编码")
            if not progress_callback: goto 246
            progress_callback(100)
            if not model_manager: goto 268
            hasattr(model_manager, 'release_model_resources')
            if not <?>: goto 268
            model_manager.release_model_resources()
        return {'一阶编码': first_level_codes, '二阶编码': second_level_codes, '三阶编码': third_level_codes, 'file_sentence_mapping': file_sentence_mapping}
            # except matching at 406
            Exception
            e = Exception
            # try:
            str(e)
            <?>("logger.errorstr('生成多文件编码失败: ')")
            traceback = <?>
            traceback.print_exc()
            if not model_manager: goto 356
            hasattr(model_manager, 'release_model_resources')
            if not <?>: goto 356
            model_manager.release_model_resources()
            # except:
            e = None
            del e
        return ['请检查输入文本']
        e = None
        del e
        raise '错误'

        raise
        {'一阶编码': '错误', '二阶编码': ['系统故障'], '三阶编码': {}}
        {}
        {}
        ['生成编码时出现错误']
        '错误'

    def generate_first_level_codes(self, sentences, model_manager, coding_options):
        self.reset_first_level_trace_meta()
        first_level_codes = {}
        trace_items = []
        if coding_options: goto 24 (or pop)
        {}.get('use_global_batch_rerank', False)
        bool(coding_options)
        use_global_batch_rerank = <?>
        enumerate(sentences)
            # for loop body, delta=316
            <var0>, <var1> = iter(<?>)
            i = <?>
            sentence = <?>

            # try:
            sentence.get('content', '')
            content = <?>
            sentence.get('speaker', '')
            speaker = <?>
            if not speaker: goto 94
            if not (speaker != 'respondent'): goto 94
            # goto 44
            if not content: goto 254
            content.strip()
            <?>(self._is_coding_worthy_sentence)
            if not <?>: goto 254
            code_key = "(i + 1)format('04d')"
            self.build_first_level_candidate_trace(content, model_manager=model_manager, defer_rerank=use_global_batch_rerank)
            trace = 'FL_'
            trace_items.append((code_key, sentence, trace))
            if use_global_batch_rerank: goto 254
            self._repair_first_level_sentence_detail(sentence)
            source_detail = <?>
            source_detail.get('sentence_id')
            if <?>: goto 200
            self._store_first_level_trace(code_key, trace)
            # goto 44
            self._select_quality_first_level_candidate(trace, source_detail)
            selected_candidate = <?>
            self._store_first_level_trace(code_key, trace)
            if selected_candidate: goto 232
            # goto 44
            [selected_candidate, [source_detail], 1, 1, [source_detail]][first_level_codes] = code_key
            # goto 44
            # except matching at 314
            Exception
            e = Exception
            # try:
            logger.warning('处理句子失败 str(i): str(e)')
            # except:
            e = None
            del e
            # goto 44
            e = None
            del e
            raise 

            raise
            if not use_global_batch_rerank: goto 450
            if not trace_items: goto 450
            # def 'EnhancedCodingGenerator.generate_first_level_codes.<locals>.<listcomp>'()
            self._apply_global_batch_rerank(iter(trace_items))
            <?>(<?>, model_manager,=model_manager)
            # for loop body, delta=450
            <var0>, <var1>, <var2> = iter(trace_items)
            code_key = <?>
            sentence = <?>
            trace = <?>
            self._repair_first_level_sentence_detail(sentence)
            source_detail = <?>
            source_detail.get('sentence_id')
            if <?>: goto 396
            self._store_first_level_trace(code_key, trace)

            # goto 352
            self._select_quality_first_level_candidate(trace, source_detail)
            selected_candidate = <?>
            self._store_first_level_trace(code_key, trace)
            if selected_candidate: goto 426

            # goto 352
            [selected_candidate, [source_detail], 1, 1, [source_detail]][first_level_codes] = code_key
            # goto 352
        return first_level_codes

    def _init_rag_components(self):
            # try:
            if not Config: goto 18
            getattr(Config, 'ENABLE_RAG_CODING', False)
            if <?>: goto 24
        return None
        if not RuntimeStrategyDetector: goto 44
        if not RagIndexManager: goto 44
        if not RAGSemanticMatcher: goto 44
        if not FirstLevelClusterer: goto 44
        if CodingDecisionPolicy: goto 50
        return None
        if self.coding_library: goto 62
        return None
        RuntimeStrategyDetector()
        <?>.detect()
        <?>.runtime_strategy = self
        embedding_fn = None
        if not self.semantic_matcher: goto 100
        if not self.runtime_strategy.use_vector_clustering: goto 100
        embedding_fn = self.semantic_matcher.get_embedding
        RagIndexManager(self.coding_library.library_path, Config.RAG_INDEX_DIR, embedding_fn,=embedding_fn)
        <?>.rag_index_manager = self
        self.rag_index_manager.ensure_fresh()
        if <?>: goto 148
        logger.warning('RAG索引不可用，回退到传统语义匹配流程')
        return None
        RAGSemanticMatcher(Config.RAG_INDEX_DIR, embedding_fn,=embedding_fn)
        <?>.rag_matcher = self
        if self.rag_matcher.documents: goto 188
        logger.warning('RAG匹配器未加载到索引文档，回退到传统语义匹配流程')
        return None
        self._ensure_rag_threshold_defaults()
        self._rebuild_decision_policy_from_matcher()
        FirstLevelClusterer(embedding_fn=embedding_fn, similarity_threshold=self.rag_cluster_similarity_threshold)
        <?>.first_level_clusterer = self
        True.rag_enabled = self
        logger.info('RAG自动编码已启用，运行策略: str(self.runtime_strategy.name)')
        return None
            # except matching at 310
            Exception
            e = Exception
            # try:
            logger.warning('RAG组件初始化失败，回退旧流程: str(e)')
            False.rag_enabled = self
            # except:
            e = None
            del e
        return None
        e = None
        del e
        raise 

        raise

    def ConceptAnchorIndex(self):
        if not (self.concept_anchor_index is not None): goto 14
        return True

            # try:
            _os = <?>
            _os.path.abspath(__file__)
            _os.path.join(_os.path.dirname)
            <?>(<?>, 'cache', 'anchor_index')
            _anchor_dir = <?>
            _os.path.join(_anchor_dir, 'anchor_index.faiss')
            _faiss_path = <?>
            _os.path.join(_anchor_dir, 'concepts.json')
            _concepts_path = <?>
            _os.path.exists(_faiss_path)
            if not <?>: goto 108
            _os.path.exists(_concepts_path)
            if <?>: goto 124
            logger.info('概念锚点索引未构建，跳过概念锚点检索')
        return False
        ConceptAnchorIndex = ConceptAnchorIndex
        _os.path.abspath(__file__)
        _os.path.join(_os.path.dirname)

        <?>(<?>, 'trained_models', 'concept_anchor')
        _model_path = <?>
        _os.path.abspath(__file__)
        _os.path.join(_os.path.dirname)

        <?>(<?>, 'coding_library.json')
        _library_path = <?>
        _os.path.abspath(__file__)
        _os.path.join(_os.path.dirname)

        <?>(<?>, 'data', 'clean_anchor_pairs.json')
        _anchor_data = <?>
        _os.path.exists(_model_path)
        if <?>: goto 258
        logger.info('微调锚点模型不存在，跳过概念锚点检索')
        return False
        ConceptAnchorIndex(model_path=_model_path, library_path=_library_path, anchor_data_path=_anchor_data)
        <?>.concept_anchor_index = self
        len(self.concept_anchor_index.concepts)
        <?>(logger.info, '概念锚点FAISS索引加载成功，%d个概念')
        return True
            # except matching at 358
            Exception
            e = Exception
            # try:
            logger.warning('概念锚点索引加载失败: str(e)')
            None.concept_anchor_index = self
            # except:
            e = None
            del e
        return False
        e = None
        del e
        raise 

        raise

    def _best_candidate_names(self, candidates):
        token_best_name = None
        vector_best_name = None
        float('-inf')
        token_best = <?>
        float('-inf')
        vector_best = <?>
            # for loop body, delta=178
            cand = iter(candidates)

            # try:
            cand.get('token_score', 0.0)
            <?>(float)
            token_score = <?>
            # goto 80
            # except matching at 78
            Exception
            (TypeError, ValueError)
            token_score = 0.0
            # except:
            # goto 80

            raise

            # try:
            cand.get('vector_score', 0.0)
            <?>(float)
            vector_score = <?>
            # goto 128
            # except matching at 126
            Exception
            (TypeError, ValueError)
            vector_score = 0.0
            # except:
            # goto 128

            raise
            cand.get('name')
            name = <?>
            if name: goto 144

            # goto 28
            if not (token_score > token_best): goto 160
            token_best = token_score
            token_best_name = name
            if not (vector_score > vector_best): goto 176
            vector_best = vector_score
            vector_best_name = name
            # goto 28
        return (token_best_name, vector_best_name)

    def _build_cluster_query(self, cluster):
        if cluster.representative: goto 8 (or pop)
        return ''
        cluster.representative

    def _try_keyword_second_match(self, text, candidates):
        if not text: goto 8
        if candidates: goto 12
        return None
        jieba.lcut(text)
        <?>(set)
        query_tokens = <?>
        if query_tokens: goto 34
        return None
        best_name = None
        best_overlap = 0
            # for loop body, delta=132
            cand = iter(candidates)
            cand.get('name', '')
            name = <?>
            if name: goto 68

            # goto 46
            jieba.lcut(name)
            <?>(set)
            name_tokens = <?>
            if name_tokens: goto 88

            # goto 46
            len((query_tokens & name_tokens))
            len(query_tokens)
            <?>(max, 1)
            overlap = (<?> / <?>)
            if not (overlap > best_overlap): goto 130
            best_overlap = overlap
            best_name = name
            # goto 46
            if not (best_overlap >= 0.4): goto 148
            if not best_name: goto 148
        return best_name
        return None

    def _lookup_second_code_by_name(self, second_name):
        if not self.coding_library: goto 10
        if second_name: goto 14
        return None
        self.coding_library.get_all_second_level_codes()
            # for loop body, delta=92
            code = iter(<?>)
            code.get('name')
            if not (<?> == second_name): goto 90
            dict(code)
            normalized = <?>
            'second'[normalized] = 'level'
            code.get('id', '')
            <?>(str)
            <?>.strip()
            <?>[normalized] = 'code_id'
            normalized
        return

        # goto 24
        return None

    def _refresh_rag_matcher_if_needed(self):
        if not self.rag_enabled: goto 12
        if self.rag_index_manager: goto 16
        return None

            # try:
            self.rag_index_manager.is_fresh()
            if not <?>: goto 34
        return None
        self.rag_index_manager.ensure_fresh()
        if <?>: goto 60
        logger.warning('RAG索引刷新失败，将继续使用旧匹配流程')
        return None
        embedding_fn = None
        if not self.semantic_matcher: goto 92
        getattr(self.runtime_strategy, 'use_vector_clustering', False)
        if not <?>: goto 92
        embedding_fn = self.semantic_matcher.get_embedding
        RAGSemanticMatcher(Config.RAG_INDEX_DIR, embedding_fn,=embedding_fn)
        <?>.rag_matcher = self
        self._rebuild_decision_policy_from_matcher()
        logger.info('检测到编码库变更，已自动刷新RAG派生索引与匹配器')
        return None
            # except matching at 184
            Exception
            e = Exception
            # try:
            logger.warning('RAG索引运行时刷新失败: str(e)')
            # except:
            e = None
            del e
        return None
        e = None
        del e
        raise 

        raise

    def generate_second_level_codes_improved(self, first_level_codes, model_manager):
        self._ensure_rag_threshold_defaults()
        if first_level_codes: goto 20
        return {}
        len(first_level_codes)
        []("logger.infostr('开始二阶编码分类，共 ') 个一阶编码")
        '无内容'
        {}._second_level_decision_meta = self
        self._refresh_rag_matcher_if_needed()
        if not self.rag_enabled: goto 480
        if not self.rag_matcher: goto 480
        if not self.decision_policy: goto 480
        if not self.first_level_clusterer: goto 480

            # try:
            self.first_level_clusterer.cluster(first_level_codes)
            clusters = <?>
            defaultdict(list)
            categories = <?>
            getattr(Config, 'RAG_FINAL_TOP_K', 5)
            1(int)
            <?>(<?>, max)
            top_k = <?>
            getattr(Config, 'RAG_TOKEN_TOP_K', 80)

            int(getattr, self.runtime_strategy, 'token_top_k')

            max(1)

            <?>(<?>, <?>)
            token_top_k = <?>
            # for loop body, delta=374
            cluster = iter(clusters)
            self._build_cluster_query(cluster)
            text = <?>
            text.strip()
            if <?>: goto 204
            categories[self.decision_policy.other_second_name].extend(cluster.source_keys)

            # goto 160
            self.rag_matcher.match_first_level_to_second_level(text, top_k=top_k, token_top_k=token_top_k)
            candidates = <?>
            self._best_candidate_names(candidates)
            <var0>, <var1> = <?>
            token_best = <?>
            vector_best = <?>
            max(1, cluster.support)
            <?>(candidates=self.decision_policy.decide_second_level, cluster_support=candidates, token_best_name=token_best, vector_best_name=vector_best)
            decision = <?>
            if not (decision.name == self.decision_policy.other_second_name): goto 320
            if not candidates: goto 320
            self._try_keyword_second_match(text, candidates)
            keyword_name = <?>
            if not keyword_name: goto 320
            self._lookup_second_code_by_name(keyword_name)

            <?>(CodingDecision, True, keyword_name, 'second_keyword_fallback', 0.35)
            decision = <?>
            categories[decision.name].extend(cluster.source_keys)
            if not (decision.name not in self._second_level_decision_meta): goto 372
            {'decision': decision.reason, 'code': decision.code}[self._second_level_decision_meta] = decision.name
            # goto 160
            # def 'EnhancedCodingGenerator.generate_second_level_codes_improved.<locals>.<dictcomp>'()
            categories.items()
            <?>(iter(<?>))
            result = <?>
            if not result: goto 424
            len(result)
            <?>("logger.infostr('RAG二阶编码完成: 共 ') 个类别")
        return result
        # goto 480
            # except matching at 478
            Exception
            e = Exception
            # try:
            logger.warning('RAG二阶匹配失败，回退旧流程: str(e)')
            # except:
            e = None
            del e
            # goto 480
            e = None
            del e
            raise 

            raise
            if not self.coding_library: goto 494
            if self.semantic_matcher: goto 514
            logger.warning('编码库或语义匹配器不可用，回退到关键词匹配')
            self._generate_second_level_codes_keyword_based(first_level_codes)
        return
        self.coding_library.get_all_second_level_codes()
        second_level_codes_list = <?>
        if second_level_codes_list: goto 550
        logger.warning('编码库中没有二阶编码，回退到关键词匹配')
        self._generate_second_level_codes_keyword_based(first_level_codes)
        return
        second_level_map = {}
            # for loop body, delta=590
            code = iter(second_level_codes_list)
            code.get('name')
            code_name = <?>
            if not code_name: goto 586
            code[second_level_map] = code_name
            # goto 558
            if not Config: goto 608
            getattr(Config, 'RAG_OTHER_SECOND_LEVEL_NAME', '其他各类话题')
            # goto 610
            other_second = '其他各类话题'
            # def 'EnhancedCodingGenerator.generate_second_level_codes_improved.<locals>.<dictcomp>'()
            <?>(iter(second_level_codes_list))
            categories = <?>
            [][categories] = other_second
            first_level_codes.items()
            # for loop body, delta=1314
            <var0>, <var1> = iter(<?>)
            key = <?>
            codes = <?>
            if not codes: goto 666
            # goto 668
            content = ''
            if content: goto 694
            categories[other_second].append(key)
            codes[0]
            # goto 642
            top_k = 5
            cache_key = 'str(content)_str(top_k)_0.3'
            if not (cache_key in self.similarity_cache): goto 748
            logger.info('使用缓存的相似度计算结果')
            matches = self.similarity_cache[cache_key]
            # goto 780
            self.semantic_matcher.match_first_level_to_second_level(content, second_level_codes_list, top_k=top_k, threshold=self.rag_second_level_threshold)
            matches = <?>
            matches[self.similarity_cache] = cache_key
            if not matches: goto 1264
            if not model_manager: goto 1156
            model_manager.is_trained_model_available()
            if not <?>: goto 1156
            len(matches)
            <?>("logger.infostr('使用bert_finetuned模型对 ') 个候选进行重排")
            # def 'EnhancedCodingGenerator.generate_second_level_codes_improved.<locals>.<listcomp>'()
            <?>(iter(matches))
            candidate_codes = <?>

            # try:
            # def 'EnhancedCodingGenerator.generate_second_level_codes_improved.<locals>.<listcomp>'()
            (content,)(iter(candidate_codes))
            inputs = <?>
            model_manager.predict_categories(inputs)
            <var0>, <var1> = <?>
            predictions = <?>
            _ = <?>
            confidences = []
            # for loop body, delta=928
            pred = iter(predictions)
            isinstance(pred, tuple)
            if not <?>: goto 914
            confidences.append(pred[1])
            # goto 880
            confidences.append(0.0)
            # goto 880
            if not confidences: goto 1002
            max(confidences)
            <?>(confidences.index)
            best_idx = <?>
            <var0>, <var1> = matches[best_idx]
            best_match = <?>
            _ = <?>
            best_match.get('name')
            second_cat = <?>
            max(confidences)
            logger.info("bert_finetuned模型选择的二阶编码: str(second_cat) (置信度: format('.4f'))")
            # goto 1050
            <var0>, <var1> = matches[0]
            best_match = <?>
            similarity = <?>
            best_match.get('name')
            second_cat = <?>
            "回退到相似度匹配: '"("str(second_cat) (相似度: similarityformat('.4f'))")
            logger.info
            # goto 1218
            # except matching at 1154
            Exception
            e = Exception
            # try:
            logger.warning('模型重排失败，回退到相似度匹配: str(e)')
            <var0>, <var1> = matches[0]
            best_match = <?>
            similarity = <?>
            best_match.get('name')
            second_cat = <?>
            "回退到相似度匹配: '"("str(second_cat) (相似度: similarityformat('.4f'))")
            logger.info
            # except:
            e = None
            del e
            # goto 1218
            e = None
            del e
            raise 

            raise
            <var0>, <var1> = matches[0]
            best_match = <?>
            similarity = <?>
            best_match.get('name')
            second_cat = <?>
            "一阶编码 '"("str(content[slice(None, 30)])...' 匹配到二阶编码 str(second_cat) (相似度: similarityformat('.4f'))")
            logger.info
            if not (second_cat in categories): goto 1246
            categories[second_cat].append(key)
            # goto 642
            categories[other_second].append(key)
            # goto 642
            logger.info("一阶编码 str(content[slice(None, 30)])...' 未找到匹配的二阶编码，归类为str(other_second)")
            categories[other_second].append(key)
            # goto 642
            len(categories)
            <?>("logger.infostr('二阶编码完成: 共 ') 个类别")
            # def 'EnhancedCodingGenerator.generate_second_level_codes_improved.<locals>.<dictcomp>'()
            categories.items()
            <?>(iter(<?>))
            result = <?>
        return result

    def _generate_second_level_codes_keyword_based(self, first_level_codes):
        keyword_map = {'团队职责与架构': [], '质量管理与控制': ('危机', '挑战', '困难', '问题', '应对', '解决', '突破'), '技术创新与研发': [], '危机挑战与应对': ('迷茫', '方向感', '确定性', '成就感', '归属感', '荣誉感', '氛围'), '团队心理与氛围': [], '领导力与决策': ('领导', '管理', '决策', '资源', '协调', '支持', '目标')}
        # def 'EnhancedCodingGenerator._generate_second_level_codes_keyword_based.<locals>.<dictcomp>'()
        keyword_map.keys()
        [](iter(('创新', '方法', '技术', '研发', '开发', '测试方法', '检测技术')))
        categories = ('质量', '检测', '测试', '检验', '把关', '评审', '评估', '标准')
        [][categories] = '其他各类话题'
        first_level_codes.items()
            # for loop body, delta=198
            <var0>, <var1> = iter([])
            key = ('团队', '部门', '职责', '角色', '架构', '层级', '负责', '职能')
            codes = []
            if not codes: goto 100
            codes[0].lower()
            # goto 102
            content = ''
            categorized = False
            keyword_map.items()
            # for loop body, delta=178
            <var0>, <var1> = iter(<?>)
            category = <?>
            keywords = <?>
            # def 'EnhancedCodingGenerator._generate_second_level_codes_keyword_based.<locals>.<genexpr>'()
            (content,)(iter(keywords))
            <?>(sum)
            keyword_count = <?>
            if not (keyword_count >= 1): goto 176
            categories[category].append(key)
            categorized = True
            # goto 178

            # goto 116
            if categorized: goto 196
            categories['其他各类话题'].append(key)
            # goto 76
            # def 'EnhancedCodingGenerator._generate_second_level_codes_keyword_based.<locals>.<dictcomp>'()
            categories.items()
            <?>(iter(<?>))
            result = <?>
        return result

    def generate_third_level_codes_improved(self, second_level_codes):
        self._ensure_rag_threshold_defaults()
        if second_level_codes: goto 20
        return {}
        second_level_codes.keys()
        [](list)
        category_names = '核心主题'
        len(category_names)
        <?>("logger.infostr('开始三阶编码抽象，共 ') 个二阶编码")
        if not self.rag_enabled: goto 310
        if not self.decision_policy: goto 310

            # try:
            defaultdict(list)
            third_level_categories = <?>
            # for loop body, delta=204
            second_category = iter(category_names)
            if not (second_category == self.decision_policy.other_second_name): goto 116
            third_level_categories[self.decision_policy.other_third_name].append(second_category)

            # goto 80
            self._second_level_decision_meta.get(second_category, {})
            meta = <?>
            isinstance(meta, dict)
            if not <?>: goto 150
            meta.get('code')
            # goto 152
            second_code = None
            isinstance(second_code, dict)
            if <?>: goto 174
            self._lookup_second_code_by_name(second_category)
            second_code = <?>
            self.decision_policy.decide_third_level(second_code)
            decision = <?>
            third_level_categories[decision.name].append(second_category)
            # goto 80
            # def 'EnhancedCodingGenerator.generate_third_level_codes_improved.<locals>.<dictcomp>'()
            third_level_categories.items()
            <?>(iter(<?>))
            result = <?>
            if not result: goto 254
            len(result)
            <?>("logger.infostr('RAG三阶编码完成: 共 ') 个类别")
        return result
        # goto 310
            # except matching at 308
            Exception
            e = Exception
            # try:
            logger.warning('RAG三阶匹配失败，回退旧流程: str(e)')
            # except:
            e = None
            del e
            # goto 310
            e = None
            del e
            raise 

            raise
            if not self.coding_library: goto 322
            if self.semantic_matcher: goto 342
            logger.warning('编码库或语义匹配器不可用，回退到规则匹配')
            self._generate_third_level_codes_rule_based(second_level_codes)
        return
        if not Config: goto 358
        getattr(Config, 'RAG_OTHER_SECOND_LEVEL_NAME', '其他各类话题')
        # goto 360
        other_second = '其他各类话题'
        if not Config: goto 378
        getattr(Config, 'RAG_OTHER_THIRD_LEVEL_NAME', '其他重要维度')
        # goto 380
        other_third = '其他重要维度'
        self.coding_library.get_all_second_level_codes()
        second_level_codes_list = <?>
        self.coding_library.get_all_third_level_codes()
        third_level_codes_list = <?>
        if not second_level_codes_list: goto 410
        if third_level_codes_list: goto 430
        logger.warning('编码库中没有二阶或三阶编码，回退到规则匹配')
        self._generate_third_level_codes_rule_based(second_level_codes)
        return
        second_level_map = {}
            # for loop body, delta=466
            code = iter(second_level_codes_list)
            code.get('name')
            code_name = <?>
            if not code_name: goto 464
            code[second_level_map] = code_name
            # goto 438
            third_level_map = {}
            # for loop body, delta=502
            code = iter(third_level_codes_list)
            code.get('name')
            code_name = <?>
            if not code_name: goto 500
            code[third_level_map] = code_name
            # goto 474
            third_level_categories = {}
            # for loop body, delta=776
            second_category = iter(category_names)
            if not (second_category == other_second): goto 558
            if not (other_third not in third_level_categories): goto 542
            [][third_level_categories] = other_third
            third_level_categories[other_third].append(second_category)

            # goto 510
            second_level_map.get(second_category)
            second_code = <?>
            if second_code: goto 608
            if not (other_third not in third_level_categories): goto 592
            [][third_level_categories] = other_third
            third_level_categories[other_third].append(second_category)

            # goto 510
            self.semantic_matcher.match_second_level_to_third_level(second_code, third_level_codes_list, threshold,=self.rag_third_level_threshold)
            match = <?>
            if not match: goto 718
            <var0>, <var1> = match
            best_match = <?>
            similarity = <?>
            best_match.get('name')
            third_cat = <?>
            "二阶编码 '"("str(second_category) 匹配到三阶编码 str(third_cat) (相似度: similarityformat('.4f'))")
            logger.info
            if not (third_cat not in third_level_categories): goto 702
            [][third_level_categories] = third_cat
            third_level_categories[third_cat].append(second_category)
            # goto 510
            logger.info('二阶编码 str(second_category) 未找到匹配的三阶编码，归类为str(other_third)')
            if not (other_third not in third_level_categories): goto 760
            [][third_level_categories] = other_third
            third_level_categories[other_third].append(second_category)
            # goto 510
            if third_level_categories: goto 790
            category_names[third_level_categories] = '综合主题'
            len(third_level_categories)
            <?>("logger.infostr('生成 ') 个三阶编码")
        return third_level_categories

    def _generate_third_level_codes_rule_based(self, second_level_codes):
        if second_level_codes: goto 12
        return {}
        second_level_codes.keys()
        [](list)
        category_names = '核心主题'
        # def 'EnhancedCodingGenerator._generate_third_level_codes_rule_based.<locals>.<listcomp>'()
        <?>(iter(category_names))
        organizational_related = <?>
        # def 'EnhancedCodingGenerator._generate_third_level_codes_rule_based.<locals>.<listcomp>'()
        <?>(iter(category_names))
        technical_related = <?>
        # def 'EnhancedCodingGenerator._generate_third_level_codes_rule_based.<locals>.<listcomp>'()
        <?>(iter(category_names))
        psychological_related = <?>
        result = {}
        if not organizational_related: goto 82
        organizational_related[result] = '组织管理与架构设计'
        if not technical_related: goto 94
        technical_related[result] = '技术研发与创新应用'
        if not psychological_related: goto 106
        psychological_related[result] = '组织文化与心理氛围'
        # def 'EnhancedCodingGenerator._generate_third_level_codes_rule_based.<locals>.<listcomp>'()
        (organizational_related, psychological_related, technical_related)(iter(category_names))
        remaining = <?>
        if not remaining: goto 140
        remaining[result] = '其他重要维度'
        if result: goto 152
        category_names[result] = '综合主题'
        return result
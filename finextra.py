"""
Нагрузка плагина SPP

1/2 документ плагина
"""
from datetime import datetime, timedelta
import logging
import time
import dateparser
import dateutil.parser
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common import NoSuchElementException
from selenium.common.exceptions import TimeoutException

from src.spp.types import SPP_document


class FINEXTRA:
    """
    Класс парсера плагина SPP

    :warning Все необходимое для работы парсера должно находится внутри этого класса

    :_content_document: Это список объектов документа. При старте класса этот список должен обнулиться,
                        а затем по мере обработки источника - заполняться.


    """

    SOURCE_NAME = 'finextra'
    _content_document: list[SPP_document]

    def __init__(self, webdriver: WebDriver, last_document: SPP_document, max_count_documents: int = 100, *args, **kwargs):
        """
        Конструктор класса парсера

        По умолчанию внего ничего не передается, но если требуется (например: driver селениума), то нужно будет
        заполнить конфигурацию
        """
        # Обнуление списка
        self._content_document = []

        self.driver = webdriver
        self.max_count_documents = max_count_documents

        # Логер должен подключаться так. Вся настройка лежит на платформе
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(f"Parser class init completed")
        self.logger.info(f"Set source: {self.SOURCE_NAME}")
        ...

    def content(self) -> list[SPP_document]:
        """
        Главный метод парсера. Его будет вызывать платформа. Он вызывает метод _parse и возвращает список документов
        :return:
        :rtype:
        """
        self.logger.debug("Parse process start")
        self._parse()
        self.logger.debug("Parse process finished")
        return self._content_document

    def _parse(self):
        """
        Метод, занимающийся парсингом. Он добавляет в _content_document документы, которые получилось обработать
        :return:
        :rtype:
        """
        # HOST - это главная ссылка на источник, по которому будет "бегать" парсер
        self.logger.debug("Parser enter")

        # ========================================
        # Тут должен находится блок кода, отвечающий за парсинг конкретного источника
        # -

        current_date = datetime(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)

        # end_date = current_date - timedelta(time_delta)

        # logger.debug(f"Текущая дата: {datetime.strftime(current_date, '%Y-%m-%d')}")
        # logger.info(f"Окончательная дата: {datetime.strftime(end_date, '%Y-%m-%d')} (разница в днях: {time_delta})")

        counter = 0

        # Цикл по датам публикации
        while True:
            page_link = f"https://www.finextra.com/latest-news?date={datetime.strftime(current_date, '%Y-%m-%d')}"
            try:
                self.logger.debug(f'Загрузка: {page_link}')
                self.driver.get(page_link)
            except:
                self.logger.debug('TimeoutException:',
                            f"https://www.finextra.com/latest-news?date={datetime.strftime(current_date, '%Y-%m-%d')}")
                current_date = current_date - timedelta(1)
                # self.logger.debug(f"Изменение даты на новую: {datetime.strftime(current_date, '%Y-%m-%d')}")
                continue
            time.sleep(1)

            # Цикл по новостям за определенную дату
            while True:
                articles = self.driver.find_elements(By.XPATH, '//*[@class=\'modulegroup--latest-storylisting\']//h4/a')

                for article in articles:
                    article_url = article.get_attribute('href')

                    # link_is_in_table = False

                    # for i, df_row in df.iterrows():
                    #     if df_row['web_link'] == article_url:
                    #         self.logger.debug(f'Найдено совпадение в таблице: {df_row["web_link"]}')
                    #         link_is_in_table = True
                    #
                    # if link_is_in_table:
                    #     self.logger.debug('Ссылка на документ уже есть в таблице. Документ пропущен')
                    #     continue
                    # else:
                    # self.logger.info(f'Загрузка и обработка документа: {article_url}')
                    self.driver.execute_script("window.open('');")
                    self.driver.switch_to.window(self.driver.window_handles[1])

                    try:
                        self.driver.get(article_url)
                    except TimeoutException:
                        # self.logger.info(f'TimeoutException: {article_url}')
                        # self.logger.info('Закрытие вкладки и переход к след. материалу...')
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        continue

                    time.sleep(1)

                    try:
                        article_title = self.driver.find_element(By.CLASS_NAME, 'article--title')
                        article_type = self.driver.current_url.split('/')[3]
                        title = article_title.find_element(By.TAG_NAME, 'h1').text
                        date_text = article_title.find_element(By.CLASS_NAME, 'time--diff').text

                        date = dateparser.parse(date_text)
                        tw_count = article_title.find_element(By.CLASS_NAME, 'module--share-this').find_element(By.ID,
                                                                                                                'twitterResult').text
                        li_count = article_title.find_element(By.CLASS_NAME, 'module--share-this').find_element(By.ID,
                                                                                                                'liResult').text
                        fb_count = article_title.find_element(By.CLASS_NAME, 'module--share-this').find_element(By.ID,
                                                                                                                'fbResult').text

                        left_tags = self.driver.find_element(By.CLASS_NAME, 'article--tagging-left')

                        try:
                            related_comp = ', '.join([el.text for el in left_tags.find_elements(By.XPATH,
                                                                                                '//h4[text() = \'Related Companies\']/following-sibling::div[1]//span')
                                                      if el.text != ''])
                        except:
                            related_comp = ''

                        try:
                            lead_ch = ', '.join([el.text for el in left_tags.find_elements(By.XPATH,
                                                                                           '//h4[text() = \'Lead Channel\']/following-sibling::div[1]//span')
                                                 if el.text != ''])
                            logging_string = f'{lead_ch} - {title}'
                            # self.logger.info(logging_string.replace('[^\dA-Za-z]', ''))
                        except:
                            lead_ch = ''

                        try:
                            channels = ', '.join([el.text for el in left_tags.find_elements(By.XPATH,
                                                                                            '//h4[text() = \'Channels\']/following-sibling::div[1]//span')
                                                  if el.text != ''])
                        except:
                            channels = ''

                        try:
                            keywords = ', '.join([el.text for el in left_tags.find_elements(By.XPATH,
                                                                                            '//h4[text() = \'Keywords\']/following-sibling::div[1]//span')
                                                  if el.text != ''])
                        except:
                            keywords = ''

                        try:
                            category_name = \
                            left_tags.find_element(By.CLASS_NAME, 'category--title').find_element(By.TAG_NAME,
                                                                                                  'span').get_attribute(
                                'innerHTML').split(' |')[0]
                            category_desc = left_tags.find_element(By.CLASS_NAME, 'category--meta').get_attribute(
                                'innerHTML')
                        except:
                            category_name = ''
                            category_desc = ''

                        abstract = self.driver.find_element(By.CLASS_NAME, 'article--body').find_element(By.CLASS_NAME,
                                                                                                    'stand-first').text
                        text = self.driver.find_element(By.CLASS_NAME, 'article--body').text
                        comment_count = self.driver.find_element(By.ID, 'comment').find_element(By.XPATH,
                                                                                           './following-sibling::h4').text.split()[
                            1].split('(', 1)[1].split(')')[0]

                        # file_name = article_url.split('/')[-1] + '.txt'
                        #
                        # with open(downloads_dir + file_name, "w", encoding='utf-8') as text_file:
                        #     text_file.write(str(text))

                        # self.logger.debug('Добавление строки в датафрейм...')

                        # row_data_list = [df.shape[0] - 1, title, datetime.strftime(date, format='%Y-%m-%d %H:%M:%S'),
                        #                  abstract, str(text),
                        #                  article_url, downloads_dir + file_name,
                        #                  datetime.strftime(datetime.now(), format='%Y-%m-%d %H:%M:%S'),
                        #                  article_type, related_comp, lead_ch, channels, keywords, category_name,
                        #                  category_desc, tw_count, li_count, fb_count, comment_count]
                        #
                        # df.loc[df.shape[0]] = row_data_list

                        other_data = {}

                        doc = SPP_document(None,
                                           title,
                                           abstract,
                                           str(text),
                                           article_url,
                                           None,
                                           other_data,
                                           date,
                                           datetime.now())
                        self._content_document.append(doc)


                        # Логирование найденного документа
                        self.logger.info(self._find_document_text_for_logger(doc))
                        counter += 1

                        if counter > self.max_count_documents:
                            return


                    except:
                        # logger.exception(f'Ошибка при обработке: {article_url}')
                        # logger.info('Закрытие вкладки и переход к след. материалу...')
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        continue

                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])

                try:
                    pagination = self.driver.find_element(By.ID, 'pagination')
                    next_page_url = pagination.find_element(By.XPATH, '//*[text() = \'›\']').get_attribute('href')
                    self.driver.get(next_page_url)
                except Exception as e:
                    # logger.info('Пагинация не найдена. Прерывание обработки страницы')
                    break

            current_date = current_date - timedelta(1)
            # logger.info(f"Изменение даты на новую: {datetime.strftime(current_date, '%Y-%m-%d')}")

            # if current_date < end_date:
            #     logger.info('Текущая дата меньше окончательной даты. Прерывание парсинга.')
            #     break

        # df.to_csv(df_path, index=False, sep='\t')
        #
        # logger.info(f'Датарфейм сохранен: {df_path}')
        #
        # logger.info(f'Парсинг Finextra закончен. Новых материалов: {counter}')

        self.driver.close()
        self.driver.quit()



        # ---
        # ========================================
        ...

    @staticmethod
    def _find_document_text_for_logger(doc: SPP_document):
        """
        Единый для всех парсеров метод, который подготовит на основе SPP_document строку для логера
        :param doc: Документ, полученный парсером во время своей работы
        :type doc:
        :return: Строка для логера на основе документа
        :rtype:
        """
        return f"Find document | name: {doc.title} | link to web: {doc.web_link} | publication date: {doc.pub_date}"

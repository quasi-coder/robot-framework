#sudo apt-get install libtiff5-dev
from PIL import Image,TiffImagePlugin
from PIL import ImageChops
import shutil

import os
import math

class ImageComparsion:
    '''
    Library provides keywords for tiff image comparison
    '''
    def get_tiff_page_count(self, path_to_tiff_pack):
        '''
        Get count of images from multipage tiff

        example:
        | Get Tiff Page Count | ${path_to_tiff} |

        '''
        page_count = 0
        tiff_archive = Image.open(path_to_tiff_pack)
        while True:
            try:
                tiff_archive.seek(page_count)
            except EOFError:
                break
            page_count += 1

        return page_count

    def compare_multipage_tiff(self, path_to_tiff_pack, tiff_path_list, critical_value=1.):
        '''
        Compare all images from path_to_tiff_pack with all images from tiff_path_list with max percentage difference critical_value

        example:

         | Compare Multipage Tiff | ${tiff_archive_path} | ${tiff_images} |

        '''
        page = 0
        error_list = []
        tiff_archive = Image.open(path_to_tiff_pack)
        while True:

            try:
                tiff_archive.seek(page)
            except EOFError:
                break

            in_images = False
            for image_input_path in tiff_path_list:
                image2 = Image.open(image_input_path)
                diff = self._get_image_difference(tiff_archive, image2)
                if diff<critical_value:
                    in_images = True
                    tiff_path_list.remove(image_input_path)
                    break
                for i in xrange(3):
                    image2 = image2.rotate(90)
                    diff2 = self._get_image_difference(tiff_archive, image2)
                    if diff > diff2:
                        diff = diff2
                        if diff<critical_value:
                            in_images = True
                            tiff_path_list.remove(image_input_path)
                            break

            if not in_images:
                error_list.append(tiff_archive.tell()+1)

            page+=1
        if len(error_list) != 0:
            short_path = []
            for tiff_path in tiff_path_list:
                tmp = os.path.split(tiff_path)[0]
                try:
                    short_path.index(tmp)
                except:
                    short_path.append(tmp)
            raise StandardError('"%s" page(s) %s are not found in %s'%(os.path.split(path_to_tiff_pack)[1], error_list, short_path))
        return True
    def _get_image_difference(self, image1, image2):
        ''' Compare two images from paths with critical value
        :param image_input_path:                path to first image for compare
        :param image_to_compare_input_path:     path to second image for compare
        :param critical_value:                  critical percentage of differences.

        :return:                     True if images equals, False otherwise
        '''
        sizex, sizey = image1.size
        if image2.size[0] < sizex: sizex = image2.size[0]
        if image2.size[1] < sizey: sizey = image2.size[1]
        image1 = image1.resize((sizex, sizey), Image.ANTIALIAS)
        image2 = image2.resize((sizex, sizey), Image.ANTIALIAS)
        try:
            dif12 = ImageChops.difference(image1.convert('RGB'), image2.convert('RGB')).convert('L')
        except:
            return False
        total_sum = 0
        for i,x in enumerate(dif12.histogram()):
            total_sum += x * (i ** 2)
            #total_sum += x * i

        current_difference = math.sqrt(float(total_sum)/(sizex*sizey))/(len(dif12.histogram())-1) * 100
        #current_difference = float(total_sum)/(sizex*sizey)/(len(dif12.histogram())-1) * 100

        ###DEBUG###
        # print  "*WARN* image_input_path", image_input_path
        # print  "*WARN* image_to_compare_input_path", image_to_compare_input_path
        #
        # debug_path = os.path.join(os.path.dirname(image_to_compare_input_path),'debug')
        # if not os.path.exists(debug_path):
        #     os.makedirs(debug_path)
        # dif12.save(os.path.join(debug_path, os.path.basename(image_to_compare_input_path) +'_with_'+ os.path.basename(image_input_path)+ '('+ str(current_difference)  +').png') ,'PNG')
        ###DEBUG###

        return current_difference

    def get_images_from_dir(self, path):
        '''
        Find all correct images in path and return  list with them

        Example:
        | ${input_images}= | Get Images From Dir | ${CURDIR}${/}input_images |
        '''
        result = [];
        if os.path.isdir(path):
            for name in os.listdir(path):
                path_to_file = os.path.join(path, name);
                try:
                    Image.open(path_to_file).verify()
                    result.append(path_to_file)
                except:
                    pass
        return result

    def get_image_difference(self, image_input_path, image_to_compare_input_path):
        '''
        compare two images from image_input_path and image_to_compare_input_path.

        return percentage difference

        example:
        | ${res} | Compare Images | ${input}${/}01.tif | ${input}${/}02.tif |
        '''
        image1 = Image.open(image_input_path)
        image2 = Image.open(image_to_compare_input_path)
        return self._get_image_difference(image1, image2)

    def compare_images(self, image_input_path, image_to_compare_input_path, critical_value=0.01):
        '''
        compare two images from image_input_path and  image_to_compare_input_path.

        Return False if percentage difference more than critical_value, otherwise return True

        example:
        | ${res} | Compare Images | ${input}${/}01.tif | ${input}${/}02.tif |
        '''
        current_difference = ImageComparsion.get_image_difference(self, image_input_path, image_to_compare_input_path)

        if current_difference < critical_value: return True
        return False

    def compare_images_in_lists(self,images_input_path, image_to_compare_input_path, critical_value=0.01):
        '''
            Check that all images from  image_to_compare_input_path equals some images from images_input_path

            Fail if some images from image_to_compare_input_path not in images_input_path otherwise return True
        '''
        in_images = False
        for image_to_compare_path in image_to_compare_input_path:
            in_images = False
            for image_input_path in images_input_path:
                if ImageComparsion.compare_images(self, image_input_path,image_to_compare_path, critical_value):
                    in_images = True
                    images_input_path.remove(image_input_path)
                    break
            if not in_images: raise StandardError('No \"%s\" in images'%os.path.basename(image_to_compare_path))
        return True

    def clear(self,image_path):
        '''
        Delete temporary directory with images from image_path

        Example:
        | Test Setup     | Clear | ${output} |
        | Test Teardown  | Clear | ${output} |
        '''
        if os.path.isdir(image_path):
            shutil.rmtree(image_path)
            return